/**
 * frappe.page hosts many sites on one app host: each editor lives under a path of it
 * (`mount`, such as /s/<sub>) and each published site on a host of its own (`live_origin`).
 * The editor shell renders this boot from the `builder_editor_boot` hook. Anywhere else it
 * is empty, so every helper here falls back to what stock Builder does.
 */
export type FrappePageBoot = {
	mount?: string;
	live_origin?: string;
	app_url?: string;
	/** the app host page that signs the user in to this site, then comes back to `redirect-to` */
	open_url?: string;
	dashboard_url?: string;
	site_subdomain?: string;
};

declare global {
	interface Window {
		fp?: FrappePageBoot;
	}
}

// globalThis: unit tests import this without a window
export const fp: FrappePageBoot = globalThis.window?.fp ?? {};
export const isMounted = Boolean(fp.mount);

/** The origin that serves the published pages. */
export const liveOrigin = () => (isMounted && fp.live_origin) || window.location.origin;

/** This site's address in the editor: the app host is shared, so the mount tells its sites apart. */
export const siteURL = () => window.location.origin + (fp.mount ?? "");

/** Where a link to the Desk goes: frappe.page sites have no Desk, so its dashboard stands in. */
export const deskURL = (path = "/app") => (isMounted && fp.dashboard_url) || path;

export const loginURL = () => {
	if (!isMounted || !fp.open_url) return "/login?redirect-to=/builder";
	const here = window.location.pathname + window.location.search;
	return `${fp.open_url}?redirect-to=${encodeURIComponent(here)}`;
};
