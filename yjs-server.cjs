#!/usr/bin/env node

console.log("Starting Yjs WebSocket Server...");

const WebSocket = require("ws");
const http = require("http");
const Y = require("yjs");
const syncProtocol = require("y-protocols/sync");
const awarenessProtocol = require("y-protocols/awareness");
const encoding = require("lib0/encoding");
const decoding = require("lib0/decoding");

console.log("Modules loaded successfully");

const port = process.env.PORT || parseInt(process.argv[2]) || 1234;

// Store documents in memory
const docs = new Map();

const messageSync = 0;
const messageAwareness = 1;

function getYDoc(docname, gc = true) {
  let doc = docs.get(docname);
  if (!doc) {
    doc = new Y.Doc();
    doc.gc = gc;
    docs.set(docname, doc);
  }
  return doc;
}

const server = http.createServer((req, res) => {
  res.writeHead(200, { "Content-Type": "text/plain" });
  res.end("Yjs WebSocket Server is running\n");
});

const wss = new WebSocket.Server({ server });

wss.on("connection", (ws, req) => {
  const url = new URL(req.url || "", `http://${req.headers.host}`);
  const docName = url.pathname.slice(1).split("/")[0];

  console.log(`New connection for document: ${docName}`);

  const doc = getYDoc(docName);
  const awareness = new awarenessProtocol.Awareness(doc);

  ws.on("message", (message) => {
    const encoder = encoding.createEncoder();
    const decoder = decoding.createDecoder(new Uint8Array(message));
    const messageType = decoding.readVarUint(decoder);

    switch (messageType) {
      case messageSync:
        encoding.writeVarUint(encoder, messageSync);
        syncProtocol.readSyncMessage(decoder, encoder, doc, ws);
        if (encoding.length(encoder) > 1) {
          ws.send(encoding.toUint8Array(encoder));
        }
        break;
      case messageAwareness:
        awarenessProtocol.applyAwarenessUpdate(
          awareness,
          decoding.readVarUint8Array(decoder),
          ws,
        );
        break;
    }
  });

  // Send sync step 1
  const encoder = encoding.createEncoder();
  encoding.writeVarUint(encoder, messageSync);
  syncProtocol.writeSyncStep1(encoder, doc);
  ws.send(encoding.toUint8Array(encoder));

  // Send awareness
  const awarenessStates = awareness.getStates();
  if (awarenessStates.size > 0) {
    const encoder = encoding.createEncoder();
    encoding.writeVarUint(encoder, messageAwareness);
    encoding.writeVarUint8Array(
      encoder,
      awarenessProtocol.encodeAwarenessUpdate(
        awareness,
        Array.from(awarenessStates.keys()),
      ),
    );
    ws.send(encoding.toUint8Array(encoder));
  }

  // Broadcast awareness updates
  awareness.on("update", ({ added, updated, removed }) => {
    const changedClients = added.concat(updated).concat(removed);
    const encoder = encoding.createEncoder();
    encoding.writeVarUint(encoder, messageAwareness);
    encoding.writeVarUint8Array(
      encoder,
      awarenessProtocol.encodeAwarenessUpdate(awareness, changedClients),
    );
    const buff = encoding.toUint8Array(encoder);

    wss.clients.forEach((client) => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(buff);
      }
    });
  });

  // Broadcast document updates
  doc.on("update", (update) => {
    const encoder = encoding.createEncoder();
    encoding.writeVarUint(encoder, messageSync);
    syncProtocol.writeUpdate(encoder, update);
    const message = encoding.toUint8Array(encoder);

    wss.clients.forEach((client) => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(message);
      }
    });
  });

  ws.on("close", () => {
    console.log(`Connection closed for document: ${docName}`);
    awareness.destroy();
  });

  ws.on("error", (error) => {
    console.error("WebSocket error:", error);
  });
});

wss.on("error", (error) => {
  console.error("WebSocket server error:", error);
});

server.listen(port, () => {
  console.log(`✅ Yjs WebSocket server running on port ${port}`);
  console.log(`   WebSocket URL: ws://localhost:${port}`);
  console.log(`   HTTP URL: http://localhost:${port}`);
});

// Graceful shutdown
process.on("SIGINT", () => {
  console.log("\n🛑 Shutting down gracefully...");
  wss.close(() => {
    server.close(() => {
      console.log("✅ Server closed");
      process.exit(0);
    });
  });
});

process.on("SIGTERM", () => {
  console.log("\n🛑 SIGTERM received, shutting down...");
  wss.close(() => {
    server.close(() => {
      process.exit(0);
    });
  });
});
