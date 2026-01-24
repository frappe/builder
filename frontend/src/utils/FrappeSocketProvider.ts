import * as decoding from "lib0/decoding";
import * as encoding from "lib0/encoding";
import { Socket } from "socket.io-client";
import * as awarenessProtocol from "y-protocols/awareness";
import { Awareness } from "y-protocols/awareness";
import * as syncProtocol from "y-protocols/sync";
import * as Y from "yjs";

const MESSAGE_SYNC = 0;
const MESSAGE_AWARENESS = 1;

export interface FrappeSocketProviderOptions {
	autoConnect?: boolean;
	awareness?: Awareness;
	resyncInterval?: number;
	socket?: Socket; // Existing socket from Frappe UI
}

/**
 * Custom Yjs provider that integrates with Frappe's socket.io infrastructure
 */
export class FrappeSocketProvider {
	public doc: Y.Doc;
	public awareness: Awareness;
	public socket: Socket;
	public roomName: string;
	public connected = false;
	public synced = false;

	private autoConnect: boolean;
	private resyncInterval: number;
	private resyncTimer: ReturnType<typeof setInterval> | null = null;
	private eventHandlers: Map<string, Set<(...args: any[]) => void>> = new Map();

	constructor(roomName: string, doc: Y.Doc, socket: Socket, options: FrappeSocketProviderOptions = {}) {
		this.roomName = roomName;
		this.doc = doc;
		this.socket = socket;
		this.awareness = options.awareness || new Awareness(doc);
		this.autoConnect = options.autoConnect !== false;
		this.resyncInterval = options.resyncInterval || -1;

		// Set up document update listener
		this.doc.on("update", this.onDocUpdate);

		// Set up awareness update listener
		this.awareness.on("update", this.onAwarenessUpdate);

		if (this.autoConnect) {
			this.connect();
		}
	}

	/**
	/**
	 * Connect to Frappe's socket.io server
	 */
	connect(): void {
		console.log("Setting up Yjs collaboration on Frappe socket for:", this.roomName);

		// Set up socket event listeners
		this.socket.on("yjs-message", this.onYjsMessage);

		// If already connected, trigger connect handler immediately
		if (this.socket.connected) {
			this.onConnect();
		} else {
			// Wait for connection
			this.socket.once("connect", this.onConnect);
		}

		// Listen for disconnections
		this.socket.on("disconnect", this.onDisconnect);
	}

	/**
	 * Disconnect from socket
	 */
	disconnect(): void {
		if (this.resyncTimer) {
			clearInterval(this.resyncTimer);
			this.resyncTimer = null;
		}

		// Remove our event listeners but don't disconnect the socket
		this.socket.emit("yjs-disconnect");
		this.socket.off("connect", this.onConnect);
		this.socket.off("disconnect", this.onDisconnect);
		this.socket.off("yjs-message", this.onYjsMessage);

		this.connected = false;
		this.synced = false;
	}

	/**
	 * Destroy the provider
	 */
	destroy(): void {
		this.doc.off("update", this.onDocUpdate);
		this.awareness.off("update", this.onAwarenessUpdate);
		this.disconnect();
		this.awareness.destroy();
	}

	/**
	 * Event emitter - on
	 */
	on(event: string, handler: (...args: any[]) => void): void {
		if (!this.eventHandlers.has(event)) {
			this.eventHandlers.set(event, new Set());
		}
		this.eventHandlers.get(event)!.add(handler);
	}

	/**
	 * Event emitter - off
	 */
	off(event: string, handler: (...args: any[]) => void): void {
		const handlers = this.eventHandlers.get(event);
		if (handlers) {
			handlers.delete(handler);
		}
	}

	/**
	 * Event emitter - emit
	 */
	private emit(event: string, ...args: any[]): void {
		const handlers = this.eventHandlers.get(event);
		if (handlers) {
			handlers.forEach((handler) => handler(...args));
		}
	}

	/**
	 * Handle socket connection
	 */
	private onConnect = (): void => {
		console.log("Frappe socket.io connected for Yjs:", this.roomName);
		this.connected = true;

		// Join the Yjs document room
		this.socket.emit("yjs-connect", { docname: this.roomName });

		// Set up resync interval if specified
		if (this.resyncInterval > 0 && !this.resyncTimer) {
			this.resyncTimer = setInterval(() => {
				if (this.socket && this.connected) {
					this.sendSyncStep1();
				}
			}, this.resyncInterval);
		}

		this.emit("status", { status: "connected" });
	};

	/**
	 * Handle socket disconnection
	 */
	private onDisconnect = (): void => {
		console.log("Frappe socket.io disconnected for Yjs");
		this.connected = false;
		this.synced = false;

		if (this.resyncTimer) {
			clearInterval(this.resyncTimer);
			this.resyncTimer = null;
		}

		this.emit("status", { status: "disconnected" });
	};

	/**
	 * Handle document updates
	 */
	private onDocUpdate = (update: Uint8Array, origin: any): void => {
		// Don't send updates that came from the socket
		if (origin === this) {
			return;
		}

		// Encode and send the update
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, MESSAGE_SYNC);
		syncProtocol.writeUpdate(encoder, update);
		const message = encoding.toUint8Array(encoder);

		this.socket.emit("yjs-message", Array.from(message));
	};

	/**
	 * Handle awareness updates
	 */
	private onAwarenessUpdate = (
		{ added, updated, removed }: { added: number[]; updated: number[]; removed: number[] },
		origin: any,
	): void => {
		// Don't send updates that came from the socket
		if (origin === this) {
			return;
		}

		const changedClients = added.concat(updated).concat(removed);
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, MESSAGE_AWARENESS);
		encoding.writeVarUint8Array(
			encoder,
			awarenessProtocol.encodeAwarenessUpdate(this.awareness, changedClients),
		);
		const message = encoding.toUint8Array(encoder);

		this.socket.emit("yjs-message", Array.from(message));
	};

	/**
	 * Handle incoming Yjs messages from socket
	 */
	private onYjsMessage = (message: number[]): void => {
		const uint8Message = new Uint8Array(message);
		const decoder = decoding.createDecoder(uint8Message);
		const messageType = decoding.readVarUint(decoder);

		switch (messageType) {
			case MESSAGE_SYNC: {
				const encoder = encoding.createEncoder();
				encoding.writeVarUint(encoder, MESSAGE_SYNC);
				syncProtocol.readSyncMessage(decoder, encoder, this.doc, this);

				// If we have a response, send it back
				if (encoding.length(encoder) > 1) {
					this.socket.emit("yjs-message", Array.from(encoding.toUint8Array(encoder)));
				}

				// Mark as synced after first sync
				if (!this.synced) {
					this.synced = true;
					this.emit("synced", true);
				}
				break;
			}

			case MESSAGE_AWARENESS: {
				awarenessProtocol.applyAwarenessUpdate(this.awareness, decoding.readVarUint8Array(decoder), this);
				break;
			}

			default:
				console.warn(`Unknown Yjs message type: ${messageType}`);
		}
	};

	/**
	 * Send sync step 1 to request document state
	 */
	private sendSyncStep1(): void {
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, MESSAGE_SYNC);
		syncProtocol.writeSyncStep1(encoder, this.doc);
		const message = encoding.toUint8Array(encoder);
		this.socket.emit("yjs-message", Array.from(message));
	}
}
