import { getCurrentInstance, onBeforeUnmount, onMounted, ref, Ref } from "vue";
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
	updateLocalSelection: (blockIds: string[]) => void;
	getData: () => any;
}

/**
 * Vue composable for Yjs collaborative editing
 */
export function useYjsCollaboration(options: UseYjsCollaborationOptions): UseYjsCollaborationReturn {
	console.log("useYjsCollaboration called with options:", options);
	const ydoc = ref<Y.Doc | null>(null);
	const provider = ref<FrappeSocketProvider | null>(null);
	const isConnected = ref(false);
	const isSynced = ref(false);
	const remoteUsers = ref<Map<number, UserAwareness>>(new Map());
	const userColor = ref(generateUserColor());

	// Y.Map to store the page data
	let ymap: Y.Map<any> | null = null;
	let isLocalUpdate = false;

	/**
	 * Initialize Yjs document and provider
	 */
	const initialize = () => {
		// Get Frappe's existing socket from Vue global properties
		const instance = getCurrentInstance();
		const $socket = instance?.appContext.config.globalProperties.$socket;

		if (!$socket) {
			console.error("Frappe socket ($socket) not available");
			return;
		}

		// Create Yjs document
		console.log("Initializing Yjs collaboration for document:", options.documentName);
		ydoc.value = createYjsDocument();
		ymap = ydoc.value.getMap("pageData");

		// Create Frappe Socket.IO provider with existing socket
		provider.value = createFrappeSocketProvider(
			ydoc.value,
			options.documentName,
			$socket, // Pass Frappe's existing socket
		) as FrappeSocketProvider;

		// Set up awareness for user presence
		if (provider.value?.awareness) {
			setupAwareness(
				provider.value.awareness,
				options.userId,
				options.userName,
				userColor.value,
				options.userImage,
			);
		}

		// Listen to connection status
		provider.value?.on("status", (event: { status: string }) => {
			isConnected.value = event.status === "connected";
		});

		// Listen to sync status
		provider.value?.on("synced", (syncStatus: boolean) => {
			isSynced.value = syncStatus;
		});

		// Listen to remote updates on the Y.Map
		ymap.observe((event) => {
			if (!isLocalUpdate && options.onRemoteUpdate) {
				const data = yMapToObject(ymap!);
				options.onRemoteUpdate(data);
			}
		});

		// Listen to awareness changes (user presence)
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

	/**
	 * Update local data and sync with Yjs
	 */
	const updateLocalData = (data: any) => {
		if (!ymap) return;

		// Set flag to prevent triggering remote update callback
		isLocalUpdate = true;

		// Sync the data to Y.Map in a transaction
		ydoc.value?.transact(() => {
			syncYMapWithObject(ymap!, data);
		});

		// Reset flag after a short delay
		setTimeout(() => {
			isLocalUpdate = false;
		}, 100);
	};

	/**
	 * Update local cursor position
	 */
	const updateLocalCursor = (blockId: string | null, position: { x: number; y: number } | null) => {
		if (provider.value?.awareness) {
			updateCursor(provider.value.awareness, blockId, position);
		}
	};

	/**
	 * Update local selection
	 */
	const updateLocalSelection = (blockIds: string[]) => {
		if (provider.value?.awareness) {
			updateSelection(provider.value.awareness, blockIds);
		}
	};

	/**
	 * Get current data from Y.Map
	 */
	const getData = (): any => {
		if (!ymap) return null;
		return yMapToObject(ymap);
	};

	// Initialize on mount
	initialize();
	onMounted(() => {});

	// Cleanup function
	const cleanup = () => {
		if (provider.value && ydoc.value) {
			const prov = provider.value as FrappeSocketProvider;
			// Set local awareness state to null before destroying to signal disconnect
			if (prov.awareness) {
				prov.awareness.setLocalState(null);
			}
			cleanupYjs(prov, ydoc.value);
		}
	};

	// Cleanup on unmount
	onBeforeUnmount(cleanup);

	// Also cleanup on page unload (tab close, navigation, etc.)
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
