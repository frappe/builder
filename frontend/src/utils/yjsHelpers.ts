import { Awareness } from "y-protocols/awareness";
import { WebsocketProvider } from "y-websocket";
import * as Y from "yjs";

export interface YjsConfig {
	documentName: string;
	websocketUrl?: string;
	awareness?: Awareness;
}

export interface UserAwareness {
	userId: string;
	userName: string;
	userColor: string;
	userImage?: string;
	cursor?: {
		blockId: string | null;
		position: { x: number; y: number } | null;
	};
	selection?: {
		blockIds: Set<string>;
	};
}

/**
 * Generate a random color for a user
 */
export function generateUserColor(): string {
	const colors = [
		"#FF6B6B",
		"#4ECDC4",
		"#45B7D1",
		"#FFA07A",
		"#98D8C8",
		"#F7DC6F",
		"#BB8FCE",
		"#85C1E2",
		"#F8B739",
		"#52B788",
	];
	return colors[Math.floor(Math.random() * colors.length)];
}

/**
 * Create a new Yjs document
 */
export function createYjsDocument(): Y.Doc {
	return new Y.Doc();
}

/**
 * Create a WebSocket provider for Yjs
 * This connects to a WebSocket server for syncing the document
 */
export function createWebsocketProvider(
	doc: Y.Doc,
	documentName: string,
	websocketUrl?: string,
): WebsocketProvider {
	// Default to the Frappe websocket if not provided
	const wsUrl = "ws://localhost:1234" || getDefaultWebsocketUrl();

	const provider = new WebsocketProvider(wsUrl, documentName, doc, {
		connect: true,
		awareness: new Awareness(doc),
	});

	return provider;
}

/**
 * Get the default WebSocket URL from the current window location
 */
function getDefaultWebsocketUrl(): string {
	const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
	const host = window.location.host;
	console.log("Default WebSocket URL:", `${protocol}//${host}`);
	return `${protocol}//${host}`;
}

/**
 * Sync Yjs Map with a JavaScript object
 */
export function syncYMapWithObject(ymap: Y.Map<any>, obj: any) {
	// Remove keys that don't exist in the object
	ymap.forEach((value, key) => {
		if (!(key in obj)) {
			ymap.delete(key);
		}
	});

	// Add or update keys from the object
	Object.entries(obj).forEach(([key, value]) => {
		if (typeof value === "object" && value !== null && !Array.isArray(value)) {
			// For nested objects, create a nested Y.Map
			let nestedMap = ymap.get(key);
			if (!(nestedMap instanceof Y.Map)) {
				nestedMap = new Y.Map();
				ymap.set(key, nestedMap);
			}
			syncYMapWithObject(nestedMap, value);
		} else {
			// For primitive values and arrays, directly set the value
			const currentValue = ymap.get(key);
			if (JSON.stringify(currentValue) !== JSON.stringify(value)) {
				ymap.set(key, value);
			}
		}
	});
}

/**
 * Convert a Y.Map to a plain JavaScript object
 */
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

/**
 * Set up awareness updates for user presence
 */
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
		cursor: null,
		selection: { blockIds: [] },
	});
}

/**
 * Update user's cursor position in awareness
 */
export function updateCursor(
	awareness: Awareness,
	blockId: string | null,
	position: { x: number; y: number } | null,
): void {
	const currentState = awareness.getLocalState();
	awareness.setLocalState({
		...currentState,
		cursor: {
			blockId,
			position,
		},
	});
}

/**
 * Update user's selection in awareness
 */
export function updateSelection(awareness: Awareness, blockIds: string[]): void {
	const currentState = awareness.getLocalState();
	awareness.setLocalState({
		...currentState,
		selection: {
			blockIds,
		},
	});
}

/**
 * Get all remote users from awareness
 */
export function getRemoteUsers(awareness: Awareness): Map<number, UserAwareness> {
	const remoteStates = new Map<number, UserAwareness>();
	const states = awareness.getStates();

	states.forEach((state, clientId) => {
		// Skip local client and clients with null/undefined state (disconnected)
		if (clientId !== awareness.clientID && state && Object.keys(state).length > 0) {
			remoteStates.set(clientId, state as UserAwareness);
		}
	});

	return remoteStates;
}

/**
 * Clean up Yjs resources
 */
export function cleanupYjs(provider: WebsocketProvider, doc: Y.Doc): void {
	provider.awareness?.destroy();
	provider.destroy();
	doc.destroy();
}
