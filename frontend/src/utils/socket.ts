import { io, type Socket } from "socket.io-client";

declare global {
	interface Window {
		site_name: string;
		socketio_port: string;
	}
}

// The FrappeUI plugin used to open this connection and hang it off
// `app.config.globalProperties.$socket`. It no longer does, so the one consumer
// (RealTimeHandler) opens it here instead.
export function createSocket(): Socket {
	return io(socketUrl(), { withCredentials: true });
}

// Behind a proxy (nginx, a tunnel) socket.io shares the page's origin, whatever its host or
// port. Only a dev web server, reached on its own port, leaves it on a port of its own.
function socketUrl(): string {
	const url = new URL(window.location.origin);
	// in dev the jinja boot data is not rendered, so the host doubles as the site and the
	// socket.io port comes from the environment
	const site = import.meta.env.DEV ? url.hostname : window.site_name;
	const port = import.meta.env.DEV ? import.meta.env.VITE_SOCKETIO_PORT || "9000" : window.socketio_port;
	if (port && url.port) url.port = port;
	return `${url.origin}/${site}`;
}
