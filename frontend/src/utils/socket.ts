import { io, type Socket } from "socket.io-client";

declare global {
	interface Window {
		site_name: string;
		socketio_port?: string;
	}
}

// The FrappeUI plugin used to open this connection and hang it off
// `app.config.globalProperties.$socket`. It no longer does, so the one consumer
// (RealTimeHandler) opens it here instead.
export function createSocket(): Socket {
	const host = window.location.hostname;
	// realtime runs as a separate node process, so its port comes from
	// common_site_config.json via boot data instead of reusing the web port
	const rawPort = window.socketio_port || "";
	const socketioPort = /^\d+$/.test(rawPort) ? rawPort : "9000";
	const port = window.location.port ? `:${socketioPort}` : "";
	const protocol = port ? "http" : "https";
	// in dev the jinja boot data is not rendered, so the host doubles as the site
	const siteName = import.meta.env.DEV ? host : window.site_name;
	return io(`${protocol}://${host}${port}/${siteName}`, { withCredentials: true });
}
