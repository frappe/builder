import { call, setConfig } from "frappe-ui";

export async function ensureSystemTimezone() {
	try {
		// Vite serves the editor without the boot payload. Read the site's zone, not the user's.
		const timezone = window.system_timezone || (await call<string>("builder.api.get_system_timezone"));
		setConfig("systemTimezone", timezone);
	} catch (error) {
		console.error("[builder] could not load the system timezone", error);
	}
}

declare global {
	interface Window {
		system_timezone?: string;
	}
}
