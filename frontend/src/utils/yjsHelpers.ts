import { Socket } from "socket.io-client";
import { Awareness } from "y-protocols/awareness";
import * as Y from "yjs";
import { FrappeSocketProvider } from "./FrappeSocketProvider";

export interface UserAwareness {
	userId: string;
	userName: string;
	userColor: string;
	userImage?: string;
	lastActive?: number; // Timestamp to track the most recently active tab
	cursor?: {
		blockId: string | null;
		position: { x: number; y: number } | null;
	};
	selection?: {
		blockIds: Set<string>;
		activeBreakpoint?: string;
	};
}

export function generateUserColor(userId?: string): string {
	const colors = [
		"#FF6B6B",
		"#4ECDC4",
		"#45B7D1",
		"#FFA07A",
		"#F7DC6F",
		"#BB8FCE",
		"#85C1E2",
		"#F8B739",
		"#52B788",
	];

	if (userId) {
		let hash = 0;
		for (let i = 0; i < userId.length; i++) {
			hash = userId.charCodeAt(i) + ((hash << 5) - hash);
		}
		return colors[Math.abs(hash) % colors.length];
	}

	return colors[Math.floor(Math.random() * colors.length)];
}

export function createYjsDocument(): Y.Doc {
	return new Y.Doc();
}

export function createFrappeSocketProvider(
	doc: Y.Doc,
	documentName: string,
	socket: Socket,
): FrappeSocketProvider {
	const provider = new FrappeSocketProvider(documentName, doc, socket, {
		autoConnect: true,
		awareness: new Awareness(doc),
		resyncInterval: 5000,
	});

	return provider;
}

export function syncYMapWithObject(ymap: Y.Map<any>, obj: any) {
	ymap.forEach((value, key) => {
		if (!(key in obj)) {
			ymap.delete(key);
		}
	});

	Object.entries(obj).forEach(([key, value]) => {
		if (typeof value === "object" && value !== null && !Array.isArray(value)) {
			let nestedMap = ymap.get(key);
			if (!(nestedMap instanceof Y.Map)) {
				nestedMap = new Y.Map();
				ymap.set(key, nestedMap);
			}
			syncYMapWithObject(nestedMap, value);
		} else {
			ymap.set(key, value);
		}
	});
}

export function yMapToObject(ymap: Y.Map<any>): any {
	const obj: any = {};
	ymap.forEach((value, key) => {
		if (value instanceof Y.Map) {
			obj[key] = yMapToObject(value);
		} else {
			obj[key] = value;
		}
	});
	return obj;
}

export function setupAwareness(
	awareness: Awareness,
	userId: string,
	userName: string,
	userColor?: string,
	userImage?: string,
): void {
	const color = userColor || generateUserColor();

	awareness.setLocalState({
		userId,
		userName,
		userColor: color,
		userImage,
		lastActive: Date.now(),
		cursor: null,
		selection: { blockIds: [], activeBreakpoint: "desktop" },
	});
}

export function updateCursor(
	awareness: Awareness,
	blockId: string | null,
	position: { x: number; y: number } | null,
): void {
	const currentState = awareness.getLocalState();
	awareness.setLocalState({
		...currentState,
		lastActive: Date.now(),
		cursor: {
			blockId,
			position,
		},
	});
}

export function updateSelection(awareness: Awareness, blockIds: string[], activeBreakpoint?: string): void {
	const currentState = awareness.getLocalState();
	awareness.setLocalState({
		...currentState,
		lastActive: Date.now(),
		selection: {
			blockIds,
			activeBreakpoint: activeBreakpoint || "desktop",
		},
	});
}

export function getRemoteUsers(awareness: Awareness): Map<number, UserAwareness> {
	const localUserId = (awareness.getLocalState() as UserAwareness)?.userId;
	const userMap = new Map<string, { clientId: number; state: UserAwareness }>();

	awareness.getStates().forEach((state, clientId) => {
		const userState = state as UserAwareness;

		const isLocalClient = clientId === awareness.clientID;
		const isEmptyState = !state || Object.keys(state).length === 0;
		const isCurrentUser = userState.userId === localUserId;

		if (isLocalClient || isEmptyState || isCurrentUser) {
			return;
		}

		if (!userState.userId) {
			return;
		}

		const existing = userMap.get(userState.userId);
		const isMoreRecent = !existing || (userState.lastActive || 0) > (existing.state.lastActive || 0);

		if (isMoreRecent) {
			userMap.set(userState.userId, { clientId, state: userState });
		}
	});

	const result = new Map<number, UserAwareness>();
	userMap.forEach(({ clientId, state }) => {
		result.set(clientId, state);
	});

	return result;
}

export function cleanupYjs(provider: FrappeSocketProvider, doc: Y.Doc): void {
	provider.awareness?.destroy();
	provider.disconnect();
	provider.destroy();
	doc.destroy();
}
