import { __ } from "@/translation";
import {
	appURL,
	ControlError,
	controlCall,
	fp,
	isMounted,
	openSiteURL,
	setControlCSRFToken,
} from "@/utils/frappePage";
import { createResource, toast } from "frappe-ui";
import { computed, reactive } from "vue";

/**
 * On frappe.page the site's address, members and custom domains live on the app host's control site, not on
 * this site: the settings panes and the site picker read them from editor_session and change them through
 * the control APIs, which stay the authority on who may do what.
 */

export type SiteRole = "Owner" | "Admin" | "Editor";

export type SiteBrief = {
	site: string;
	subdomain: string;
	status: "Active" | "Provisioning";
	role: SiteRole;
	live_url: string;
	open_url: string;
};

export type SiteMember = { user: string; full_name: string; role: SiteRole };
export type SiteInvite = { email: string; role: SiteRole; expires_on: string };
export type DNSRecord = {
	type: string;
	name: string;
	value: string;
	purpose: "verify" | "subdomain" | "apex";
};
export type SiteDomain = {
	domain: string;
	status: "Pending" | "Active";
	is_primary: 0 | 1;
	records: DNSRecord[];
};

export type SiteSummary = SiteBrief & {
	can_manage: boolean;
	primary_domain: string | null;
	next_rename_on: string | null;
	members: { members: SiteMember[]; invites?: SiteInvite[] };
	domains?: SiteDomain[];
};

export type EditorSession = {
	user: string;
	full_name: string;
	content_domain: string;
	dev_mode: boolean;
	sites: SiteBrief[];
	site: SiteSummary;
};

const api = (method: string) => `frappe_page.api.${method}`;

const state = reactive({
	session: null as EditorSession | null,
	error: "",
	/** the app host's session ended (or never was): the panes offer to sign in again */
	signedOut: false,
});
let loading: Promise<void> | null = null;

function load(): Promise<void> {
	loading ??= controlCall<EditorSession & { csrf_token: string }>(api("editor_session"), {
		subdomain: fp.site_subdomain,
	})
		.then(({ csrf_token, ...session }) => {
			setControlCSRFToken(csrf_token);
			Object.assign(state, { session, error: "", signedOut: false });
		})
		.catch((error) => {
			const signedOut = error instanceof ControlError && [401, 403].includes(error.status);
			Object.assign(state, { session: signedOut ? null : state.session, signedOut, error: errorText(error) });
		})
		.finally(() => (loading = null));
	return loading;
}

export function errorText(error: unknown) {
	return error instanceof Error ? error.message : __("Something went wrong. Try again.");
}

/** Where to sign in again: the app host's sign-in, then back to this page of the editor. */
export const signInAgainURL = () =>
	openSiteURL(fp.site_subdomain ?? "", window.location.pathname + window.location.search);

/**
 * Runs a control API that changes this site, then reloads the session so every pane shows the result.
 * Returns the API's result, or null when it failed and the toast says why; with `throws` the caller shows
 * the error itself, next to what was typed. `reload: false` is for a change the editor leaves the page after.
 */
async function change<T = unknown>(
	method: string,
	args: Record<string, string | null>,
	messages: { loading: string; success: string | ((result: T) => string) },
	{ throws = false, reload = true } = {},
): Promise<T | null> {
	const id = toast.loading(messages.loading);
	const send = () =>
		controlCall<T>(api(method), { site: state.session?.site.site ?? "", ...args }, { post: true });
	try {
		let result: T;
		try {
			result = await send();
		} catch (error) {
			// a new sign-in elsewhere replaced the control session's token: fetch it again, once
			if (!(error instanceof ControlError && error.type === "CSRFTokenError")) throw error;
			await load();
			result = await send();
		}
		if (reload) await load();
		const success = messages.success;
		toast.success(typeof success === "function" ? success(result) : success, { id });
		return result;
	} catch (error) {
		if (error instanceof ControlError && [401, 403].includes(error.status)) load();
		if (throws) {
			toast.dismiss(id);
			throw error;
		}
		toast.error(errorText(error), { id });
		return null;
	}
}

/**
 * Control logout signs the user out of every site's editor too; this editor's own session ends at once. What every
 * site's editor kept in this browser for the user goes with it, so the next person to sign in here finds none of it.
 */
async function signOut() {
	if (!state.session) await load();
	await controlCall("logout", {}, { post: true }).catch(() => null);
	await createResource({ url: "logout" })
		.submit()
		.catch(() => null);
	await fp.forgetUser?.().catch(() => null);
	window.location.href = appURL("/");
}

export function useFrappePageSite() {
	if (isMounted && !state.session && !loading && !state.signedOut) load();
	return {
		session: computed(() => state.session),
		site: computed(() => state.session?.site ?? null),
		error: computed(() => state.error),
		signedOut: computed(() => state.signedOut),
		reload: load,
		change,
		signOut,
	};
}
