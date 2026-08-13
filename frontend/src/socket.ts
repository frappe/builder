import { io } from "socket.io-client";

declare global {
	interface Window {
		site_name?: string;
	}
}

export function initSocket() {
	const host = window.location.hostname;
	const port = window.location.port ? ":9000" : "";
	const protocol = port ? "http" : "https";
	const siteName = import.meta.env.DEV ? host : window.site_name;
	return io(`${protocol}://${host}${port}/${siteName}`, { withCredentials: true });
}
