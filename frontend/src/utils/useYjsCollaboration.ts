import { getCurrentInstance, onBeforeUnmount, ref, Ref } from "vue";
import * as Y from "yjs";
import { FrappeSocketProvider } from "./FrappeSocketProvider";
import {
	cleanupYjs,
	createFrappeSocketProvider,
	createYjsDocument,
	generateUserColor,
	getRemoteUsers,
	setupAwareness,
	syncYMapWithObject,
	updateCursor,
	updateSelection,
	UserAwareness,
	yMapToObject,
} from "./yjsHelpers";

export interface UseYjsCollaborationOptions {
	documentName: string;
	userId: string;
	userName: string;
	userImage?: string;
	onRemoteUpdate?: (data: any) => void;
	onAwarenessChange?: (users: Map<number, UserAwareness>) => void;
}

export interface UseYjsCollaborationReturn {
	ydoc: Ref<Y.Doc | null>;
	provider: Ref<FrappeSocketProvider | null>;
	isConnected: Ref<boolean>;
	isSynced: Ref<boolean>;
	remoteUsers: Ref<Map<number, UserAwareness>>;
	updateLocalData: (data: any) => void;
	updateLocalCursor: (blockId: string | null, position: { x: number; y: number } | null) => void;
	updateLocalSelection: (blockIds: string[], activeBreakpoint?: string) => void;
	getData: () => any;
}

export function useYjsCollaboration(options: UseYjsCollaborationOptions): UseYjsCollaborationReturn {
	console.log("useYjsCollaboration called with options:", options);
	const ydoc = ref<Y.Doc | null>(null);
	const provider = ref<FrappeSocketProvider | null>(null);
	const isConnected = ref(false);
	const isSynced = ref(false);
	const remoteUsers = ref<Map<number, UserAwareness>>(new Map());
	const userColor = ref(generateUserColor());

	let ymap: Y.Map<any> | null = null;

	const initialize = () => {
		const instance = getCurrentInstance();
		const $socket = instance?.appContext.config.globalProperties.$socket;

		if (!$socket) {
			console.error("Frappe socket ($socket) not available");
			return;
		}

		ydoc.value = createYjsDocument();
		ymap = ydoc.value.getMap("pageData");

		provider.value = createFrappeSocketProvider(
			ydoc.value,
			options.documentName,
			$socket,
		) as FrappeSocketProvider;

		if (provider.value?.awareness) {
			setupAwareness(
				provider.value.awareness,
				options.userId,
				options.userName,
				userColor.value,
				options.userImage,
			);
		}

		provider.value?.on("status", (event: { status: string }) => {
			isConnected.value = event.status === "connected";
		});

		provider.value?.on("synced", (syncStatus: boolean) => {
			isSynced.value = syncStatus;
		});

		ymap.observe((event, transaction) => {
			if (transaction.origin !== "local" && options.onRemoteUpdate) {
				const data = yMapToObject(ymap!);
				options.onRemoteUpdate(data);
			}
		});

		if (provider.value?.awareness) {
			provider.value.awareness.on("change", () => {
				if (provider.value?.awareness) {
					remoteUsers.value = getRemoteUsers(provider.value.awareness);
					if (options.onAwarenessChange) {
						options.onAwarenessChange(remoteUsers.value);
					}
				}
			});
		}
	};

	const updateLocalData = (data: any) => {
		if (!ymap || !ydoc.value) return;

		ydoc.value.transact(() => {
			syncYMapWithObject(ymap!, data);
		}, "local");
	};

	const updateLocalCursor = (blockId: string | null, position: { x: number; y: number } | null) => {
		if (provider.value?.awareness) {
			updateCursor(provider.value.awareness, blockId, position);
		}
	};

	const updateLocalSelection = (blockIds: string[], activeBreakpoint?: string) => {
		if (provider.value?.awareness) {
			updateSelection(provider.value.awareness, blockIds, activeBreakpoint);
		}
	};

	const getData = (): any => {
		if (!ymap) return null;
		return yMapToObject(ymap);
	};

	initialize();

	const cleanup = () => {
		if (provider.value && ydoc.value) {
			const prov = provider.value as FrappeSocketProvider;
			if (prov.awareness) {
				prov.awareness.setLocalState(null);
			}
			cleanupYjs(prov, ydoc.value);
		}
	};

	onBeforeUnmount(cleanup);

	if (typeof window !== "undefined") {
		window.addEventListener("beforeunload", cleanup);
		onBeforeUnmount(() => {
			window.removeEventListener("beforeunload", cleanup);
		});
	}

	return {
		ydoc,
		provider: provider as Ref<FrappeSocketProvider | null>,
		isConnected,
		isSynced,
		remoteUsers,
		updateLocalData,
		updateLocalCursor,
		updateLocalSelection,
		getData,
	};
}
