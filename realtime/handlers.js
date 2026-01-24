/**
 * Yjs Collaboration handlers for Frappe Socket.IO
 *
 * This module handles Yjs collaboration messages through Frappe's existing socket.io infrastructure
 * instead of using a separate WebSocket server.
 */

const Y = require("yjs");
const syncProtocol = require("y-protocols/sync");
const awarenessProtocol = require("y-protocols/awareness");
const encoding = require("lib0/encoding");
const decoding = require("lib0/decoding");

// Store documents in memory
const docs = new Map();
const awareness_map = new Map();
const roomSockets = new Map(); // Map of docname to socket for broadcasting

// Message types
const MESSAGE_SYNC = 0;
const MESSAGE_AWARENESS = 1;

/**
 * Get or create a Yjs document
 */
function getYDoc(docname) {
	let doc = docs.get(docname);
	if (!doc) {
		doc = new Y.Doc();
		doc.gc = true;
		docs.set(docname, doc);

		// Set up document update listener to broadcast changes
		doc.on("update", (update, origin) => {
			// Don't broadcast if the update came from a socket (to avoid loops)
			if (origin !== "socket") {
				broadcastUpdate(docname, update);
			}
		});
	}
	return doc;
}

/**
 * Get or create awareness for a document
 */
function getAwareness(docname, doc) {
	let awareness = awareness_map.get(docname);
	if (!awareness) {
		awareness = new awarenessProtocol.Awareness(doc);
		awareness_map.set(docname, awareness);

		// Broadcast awareness updates
		awareness.on("update", ({ added, updated, removed }) => {
			const changedClients = added.concat(updated).concat(removed);
			broadcastAwareness(docname, awareness, changedClients);
		});
	}
	return awareness;
}

/**
 * Broadcast document update to all connected clients
 */
function broadcastUpdate(docname, update) {
	const encoder = encoding.createEncoder();
	encoding.writeVarUint(encoder, MESSAGE_SYNC);
	syncProtocol.writeUpdate(encoder, update);
	const message = encoding.toUint8Array(encoder);

	// Broadcast to all clients in the document room except sender
	const socket = roomSockets.get(docname);
	if (socket) {
		socket.to(docname).emit("yjs-message", Array.from(message));
	}
}

/**
 * Broadcast awareness update to all connected clients
 */
function broadcastAwareness(docname, awareness, changedClients) {
	const encoder = encoding.createEncoder();
	encoding.writeVarUint(encoder, MESSAGE_AWARENESS);
	encoding.writeVarUint8Array(encoder, awarenessProtocol.encodeAwarenessUpdate(awareness, changedClients));
	const message = encoding.toUint8Array(encoder);

	// Broadcast to all clients in the document room except sender
	const socket = roomSockets.get(docname);
	if (socket) {
		socket.to(docname).emit("yjs-message", Array.from(message));
	}
}

/**
 * Main handler function that gets called for each socket connection
 */
module.exports = function (socket) {
	console.log("Builder realtime handler initialized for socket:", socket.id);

	// Listen for Yjs collaboration requests
	socket.on("yjs-connect", (data) => {
		const docname = data.docname;
		console.log(`Yjs client connecting to document: ${docname}`);

		// Join the document room
		socket.join(docname);

		// Store socket for broadcasting (any socket in the room can be used)
		if (!roomSockets.has(docname)) {
			roomSockets.set(docname, socket);
		}

		// Get or create the Yjs document
		const doc = getYDoc(docname);
		const awareness = getAwareness(docname, doc);

		// Send initial sync state
		const encoder = encoding.createEncoder();
		encoding.writeVarUint(encoder, MESSAGE_SYNC);
		syncProtocol.writeSyncStep1(encoder, doc);
		const syncMessage = encoding.toUint8Array(encoder);
		socket.emit("yjs-message", Array.from(syncMessage));

		// Send current awareness states
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

		// Store document name on socket for cleanup
		socket.yjs_docname = docname;
	});

	// Listen for Yjs messages
	socket.on("yjs-message", (message) => {
		const docname = socket.yjs_docname;
		if (!docname) {
			console.warn("Received yjs-message without active document");
			return;
		}

		const doc = getYDoc(docname);
		const awareness = getAwareness(docname, doc);

		// Convert message array back to Uint8Array
		const uint8Message = new Uint8Array(message);
		const decoder = decoding.createDecoder(uint8Message);
		const encoder = encoding.createEncoder();
		const messageType = decoding.readVarUint(decoder);

		switch (messageType) {
			case MESSAGE_SYNC:
				encoding.writeVarUint(encoder, MESSAGE_SYNC);
				// Apply the sync message and mark origin as "socket" to prevent re-broadcast
				syncProtocol.readSyncMessage(decoder, encoder, doc, "socket");

				// Send response if there's data to send
				if (encoding.length(encoder) > 1) {
					socket.emit("yjs-message", Array.from(encoding.toUint8Array(encoder)));
				}
				break;

			case MESSAGE_AWARENESS:
				// Apply awareness update locally
				awarenessProtocol.applyAwarenessUpdate(
					awareness,
					decoding.readVarUint8Array(decoder),
					socket,
				);

				// Broadcast the awareness update to all other clients in the room
				socket.to(docname).emit("yjs-message", message);
				break;

			default:
				console.warn(`Unknown Yjs message type: ${messageType}`);
		}
	});

	// Clean up on disconnect
	socket.on("disconnect", () => {
		const docname = socket.yjs_docname;
		if (docname) {
			console.log(`Yjs client disconnected from document: ${docname}`);
			const awareness = awareness_map.get(docname);
			if (awareness) {
				// Remove the client's awareness state
				const states = Array.from(awareness.getStates().keys());
				awarenessProtocol.removeAwarenessStates(
					awareness,
					states.filter((clientId) => {
						const state = awareness.getStates().get(clientId);
						return state?.socketId === socket.id;
					}),
					null,
				);
			}
		}
	});

	// Cleanup Yjs connection
	socket.on("yjs-disconnect", () => {
		const docname = socket.yjs_docname;
		if (docname) {
			console.log(`Yjs client explicitly disconnecting from document: ${docname}`);
			socket.leave(docname);
			delete socket.yjs_docname;
		}
	});
};
