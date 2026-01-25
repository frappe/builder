const Y = require("yjs");
const syncProtocol = require("y-protocols/sync");
const awarenessProtocol = require("y-protocols/awareness");
const encoding = require("lib0/encoding");
const decoding = require("lib0/decoding");

const MESSAGE_SYNC = 0;
const MESSAGE_AWARENESS = 1;

class YjsDocumentManager {
	constructor() {
		this.docs = new Map();
		this.awarenessMap = new Map();
		this.roomSockets = new Map();
	}

	getDoc(docname) {
		let doc = this.docs.get(docname);
		if (!doc) {
			doc = new Y.Doc();
			doc.gc = true;
			this.docs.set(docname, doc);

			doc.on("update", (update, origin) => {
				if (origin !== "socket") {
					this.broadcastUpdate(docname, update);
				}
			});
		}
		return doc;
	}

	getAwareness(docname, doc) {
		let awareness = this.awarenessMap.get(docname);
		if (!awareness) {
			awareness = new awarenessProtocol.Awareness(doc);
			this.awarenessMap.set(docname, awareness);

			awareness.on("update", ({ added, updated, removed }) => {
				const changedClients = added.concat(updated).concat(removed);
				this.broadcastAwareness(docname, awareness, changedClients);
			});
		}
		return awareness;
	}

	registerSocket(docname, socket) {
		if (!this.roomSockets.has(docname)) {
			this.roomSockets.set(docname, socket);
		}
	}

	broadcastUpdate(docname, update) {
		const message = this._encodeMessage(MESSAGE_SYNC, (encoder) => {
			syncProtocol.writeUpdate(encoder, update);
		});
		this._emitToRoom(docname, message);
	}

	broadcastAwareness(docname, awareness, changedClients) {
		const message = this._encodeMessage(MESSAGE_AWARENESS, (encoder) => {
			encoding.writeVarUint8Array(
				encoder,
				awarenessProtocol.encodeAwarenessUpdate(awareness, changedClients),
			);
		});
		this._emitToRoom(docname, message);
	}

	cleanupAwareness(docname, socketId) {
		const awareness = this.awarenessMap.get(docname);
		if (awareness) {
			const states = Array.from(awareness.getStates().keys());
			const clientsToRemove = states.filter((clientId) => {
				const state = awareness.getStates().get(clientId);
				return state?.socketId === socketId;
			});
			awarenessProtocol.removeAwarenessStates(awareness, clientsToRemove, null);
		}
	}

	_encodeMessage(messageType, writeCallback) {
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, messageType);
		writeCallback(encoder);
		return Array.from(encoding.toUint8Array(encoder));
	}

	_emitToRoom(docname, message) {
		const socket = this.roomSockets.get(docname);
		if (socket) {
			socket.to(docname).emit("yjs-message", message);
		}
	}
}

class YjsMessageHandler {
	constructor(docManager) {
		this.docManager = docManager;
	}

	handleConnect(socket, docname) {
		console.log(`Yjs client connecting to document: ${docname}`);
		socket.join(docname);
		this.docManager.registerSocket(docname, socket);

		const doc = this.docManager.getDoc(docname);
		const awareness = this.docManager.getAwareness(docname, doc);

		this._sendSyncStep1(socket, doc);
		this._sendAwarenessStates(socket, awareness);

		socket.yjs_docname = docname;
	}

	handleMessage(socket, message) {
		const docname = socket.yjs_docname;
		if (!docname) {
			console.warn("Received yjs-message without active document");
			return;
		}

		const doc = this.docManager.getDoc(docname);
		const awareness = this.docManager.getAwareness(docname, doc);
		const uint8Message = new Uint8Array(message);
		const decoder = decoding.createDecoder(uint8Message);
		const messageType = decoding.readVarUint(decoder);

		switch (messageType) {
			case MESSAGE_SYNC:
				this._handleSyncMessage(socket, decoder, doc);
				break;
			case MESSAGE_AWARENESS:
				this._handleAwarenessMessage(socket, decoder, awareness, docname, message);
				break;
			default:
				console.warn(`Unknown Yjs message type: ${messageType}`);
		}
	}

	handleDisconnect(socket) {
		const docname = socket.yjs_docname;
		if (docname) {
			console.log(`Yjs client disconnected from document: ${docname}`);
			this.docManager.cleanupAwareness(docname, socket.id);
		}
	}

	handleExplicitDisconnect(socket) {
		const docname = socket.yjs_docname;
		if (docname) {
			console.log(`Yjs client explicitly disconnecting from document: ${docname}`);
			socket.leave(docname);
			delete socket.yjs_docname;
		}
	}

	_sendSyncStep1(socket, doc) {
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, MESSAGE_SYNC);
		syncProtocol.writeSyncStep1(encoder, doc);
		socket.emit("yjs-message", Array.from(encoding.toUint8Array(encoder)));
	}

	_sendAwarenessStates(socket, awareness) {
		const awarenessStates = awareness.getStates();
		if (awarenessStates.size > 0) {
			const encoder = encoding.createEncoder();
			encoding.writeVarUint(encoder, MESSAGE_AWARENESS);
			encoding.writeVarUint8Array(
				encoder,
				awarenessProtocol.encodeAwarenessUpdate(awareness, Array.from(awarenessStates.keys())),
			);
			socket.emit("yjs-message", Array.from(encoding.toUint8Array(encoder)));
		}
	}

	_handleSyncMessage(socket, decoder, doc) {
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, MESSAGE_SYNC);
		syncProtocol.readSyncMessage(decoder, encoder, doc, "socket");

		if (encoding.length(encoder) > 1) {
			socket.emit("yjs-message", Array.from(encoding.toUint8Array(encoder)));
		}
	}

	_handleAwarenessMessage(socket, decoder, awareness, docname, message) {
		awarenessProtocol.applyAwarenessUpdate(awareness, decoding.readVarUint8Array(decoder), socket);
		socket.to(docname).emit("yjs-message", message);
	}
}

const docManager = new YjsDocumentManager();
const messageHandler = new YjsMessageHandler(docManager);

module.exports = function (socket) {
	console.log("Builder realtime handler initialized for socket:", socket.id);

	socket.on("yjs-connect", (data) => {
		messageHandler.handleConnect(socket, data.docname);
	});

	socket.on("yjs-message", (message) => {
		messageHandler.handleMessage(socket, message);
	});

	socket.on("disconnect", () => {
		messageHandler.handleDisconnect(socket);
	});

	socket.on("yjs-disconnect", () => {
		messageHandler.handleExplicitDisconnect(socket);
	});
};
