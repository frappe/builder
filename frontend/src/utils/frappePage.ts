/**
 * frappe.page hosts many sites on one app host: each editor lives under a path of it
 * (`mount`, such as /s/<sub>) and each published site on a host of its own (`live_origin`).
 * The editor shell renders this boot from the `builder_editor_boot` hook. Anywhere else it
 * is empty, so every helper here falls back to what stock Builder does.
 */
export type FrappePageBoot = {
	mount?: string;
	/** where Builder's routes start: the mount itself on frappe.page, else mount + "/builder" */
	editor_base?: string;
	live_origin?: string;
	app_url?: string;
	/** the app host page that signs the user in to this site, then comes back to `redirect-to` */
	open_url?: string;
	site_subdomain?: string;
	/** who the editor was rendered for: index.html keeps each member's browser storage apart under it */
	user?: string;
	/** the description the site was created from, for its owner until onboarding hands it to Bob (promptStart.ts) */
	start?: { description: string };
	/** stylesheets index.html adds to the editor, such as how the hosting app's own blocks look in the canvas */
	stylesheets?: string[];
	/** index.html: forgets what every site's editor kept in this browser for `user`, as Sign Out does */
	forgetUser?: () => Promise<void>;
	/** fetch as it was before index.html prefixed same-origin URLs with the mount: it reaches the app host */
	appFetch?: typeof fetch;
};

declare global {
	interface Window {
		fp?: FrappePageBoot;
	}
}

// globalThis: unit tests import this without a window
export const fp: FrappePageBoot = globalThis.window?.fp ?? {};
export const isMounted = Boolean(fp.mount);
/** frappe.page/<sub>/<page>: Builder's /builder and /page segments are left out of the address */
export const shortEditorURLs = isMounted && fp.editor_base === fp.mount;

/** The editor address of a page, for full-page navigations outside the router. */
export const pageEditorURL = (pageName: string) => {
	const name = encodeURIComponent(pageName);
	if (!isMounted) return `/builder/page/${name}`;
	return shortEditorURLs ? `${fp.mount}/${name}` : `${fp.mount}/builder/page/${name}`;
};

/** The origin that serves the published pages. */
export const liveOrigin = () => (isMounted && fp.live_origin) || window.location.origin;

/** This site's address in the editor: the app host is shared, so the mount tells its sites apart. */
export const siteURL = () => window.location.origin + (fp.mount ?? "");

/** A page of the app host itself (its control site), such as /sites or /onboarding. */
export const appURL = (path: string) => `${fp.app_url ?? ""}${path}`;

/** Opens site `subdomain` in its editor: the app host signs the user in to it, then goes to `redirectTo`. */
export const openSiteURL = (subdomain: string, redirectTo?: string) => {
	const url = appURL(`/open/${encodeURIComponent(subdomain)}`);
	return redirectTo ? `${url}?redirect-to=${encodeURIComponent(redirectTo)}` : url;
};

export const loginURL = () => {
	if (!isMounted || !fp.open_url) return "/login?redirect-to=/builder";
	const here = window.location.pathname + window.location.search;
	return `${fp.open_url}?redirect-to=${encodeURIComponent(here)}`;
};

// ---------- the app host's control site ----------

/** A failed control call; `status` is the HTTP status, 0 when the server could not be reached. */
export class ControlError extends Error {
	constructor(
		message: string,
		readonly status: number,
		readonly type = "",
	) {
		super(message);
	}
}

const METHOD_PATH = /^[\w.]+$/;

/**
 * The control session's CSRF token, from editor_session. It goes only to the control site (controlCall),
 * as the tenant's own token (window.csrf_token) goes only to the tenant.
 */
let controlCSRFToken = "";

export const setControlCSRFToken = (token: string) => (controlCSRFToken = token);

/**
 * Calls whitelisted `method` on the app host's control site. The editor shares the app host's origin, and
 * the edge sends every /api that is not under a site's mount to the control site, so the request goes out
 * through the unwrapped fetch and carries the control session's cookie. GET sends `args` as the query
 * string; POST sends them as JSON with the control session's CSRF token.
 */
export async function controlCall<T = any>(
	method: string,
	args: Record<string, string | number | boolean | null | undefined> = {},
	{ post = false }: { post?: boolean } = {},
): Promise<T> {
	if (!isMounted || !fp.appFetch) throw new ControlError("Not on frappe.page", 0);
	if (!METHOD_PATH.test(method)) throw new ControlError(`Bad method ${method}`, 0);
	let url = `/api/method/${method}`;
	const headers: Record<string, string> = { Accept: "application/json" };
	const init: RequestInit = { credentials: "same-origin", headers };
	if (post) {
		init.method = "POST";
		headers["Content-Type"] = "application/json";
		headers["X-Frappe-CSRF-Token"] = controlCSRFToken;
		init.body = JSON.stringify(args);
	} else {
		const query = Object.entries(args).filter(([, value]) => value != null);
		if (query.length) url += `?${new URLSearchParams(query.map(([key, value]) => [key, String(value)]))}`;
	}

	let response: Response;
	try {
		response = await fp.appFetch(url, init);
	} catch {
		throw new ControlError("Could not reach frappe.page. Check your connection and try again.", 0);
	}
	const data = await response.json().catch(() => ({}));
	if (!response.ok)
		throw new ControlError(controlErrorMessage(data, response.status), response.status, data.exc_type);
	return data.message as T;
}

function controlErrorMessage(data: any, status: number) {
	const messages: string[] = [];
	try {
		for (const item of JSON.parse(data._server_messages || "[]")) {
			const message = JSON.parse(item).message;
			if (message) messages.push(plainText(message));
		}
	} catch {
		// not a Frappe message list
	}
	if (messages.length) return messages.join(" ");
	if (status === 429) return "Too many attempts. Wait a little and try again.";
	if (status === 403) return "You don't have access to do that.";
	if (data.exception) return plainText(String(data.exception).replace(/^[\w.]+(Error|Exception):\s*/, ""));
	return "Something went wrong. Try again.";
}

function plainText(html: string) {
	return new DOMParser().parseFromString(String(html), "text/html").body.textContent?.trim() || "";
}
