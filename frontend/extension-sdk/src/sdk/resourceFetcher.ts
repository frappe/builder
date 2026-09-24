/**
 * frappe-ui's resources, over the bridge.
 *
 * An extension frame runs at an opaque origin with no cookie, so `fetch` can
 * never reach Frappe from here. `createResource` reads its fetcher on every
 * fetch (`resources.js:57`), so one `setConfig` call reroutes every resource in
 * the frame through the port instead:
 *
 * ```js
 * import { setConfig } from "frappe-ui";
 * import builder from "frappe-builder-extension-sdk";
 *
 * setConfig("resourceFetcher", builder.data.fetcher);
 * ```
 *
 * Write it in the entry, which every frame imports. It must be the extension's
 * own `frappe-ui`: each extension bundles a copy, and the SDK cannot reach that
 * copy's config from here.
 *
 * **This is an adapter, not a gate.** It runs inside the frame, which is the
 * untrusted side, so it cannot decide anything. Each route below lands on a
 * `data.*` method the host gates and the server checks against the grant. A
 * frame that replaced this file with its own would reach exactly the same
 * methods and the same refusals.
 *
 * A URL with no route is refused rather than forwarded. Forwarding would let a
 * resource name any whitelisted method on the site, and the doctype grant would
 * stop meaning anything.
 */

import { ChannelCallError } from "../transport/createPortChannel";
import { data, type ListOptions } from "./namespaces";

type Params = Record<string, unknown>;

/** frappe-ui hands the fetcher the whole resource options, with params resolved. */
export type ResourceRequest = { url?: string; params?: Params };

const refuse = (message: string, code = "unsupported_request") =>
	new ChannelCallError({ message: `[builder] ${message}`, code });

/**
 * A plain deep copy of what a resource sent.
 *
 * `createListResource` holds its state in a `reactive`, and `makeParams` hands
 * those values straight to the fetcher — `out.fields` is a proxy over an array,
 * `out.filters` a proxy over an object. `postMessage` cannot clone a proxy, so
 * the params are flattened here, at the edge, before anything tries to send
 * them. The host flattens the answer coming back for the same reason.
 */
const asParams = (value: unknown): Params =>
	value ? (JSON.parse(JSON.stringify(value)) as Params) : {};

const named = (params: Params, field: string, url: string) => {
	const value = params[field];
	if (typeof value !== "string" || !value) {
		throw refuse(`${url} needs a "${field}".`, "invalid_params");
	}
	return value;
};

/**
 * `set_value` carries its patch as `fieldname`, which is an object from every
 * frappe-ui path. The one-field form, `fieldname` plus `value`, is what a
 * hand-written `createResource` sends, so both are read here.
 */
const patchOf = (params: Params) => {
	const sent = params.fieldname;
	if (typeof sent === "string") return { [sent]: params.value };
	if (!sent || typeof sent !== "object") {
		throw refuse("frappe.client.set_value needs a \"fieldname\".", "invalid_params");
	}
	return sent as Params;
};

const listOptions = (params: Params): ListOptions => ({
	fields: params.fields as string[],
	filters: params.filters as ListOptions["filters"],
	orFilters: params.or_filters as ListOptions["filters"],
	orderBy: params.order_by as string,
	groupBy: params.group_by as string,
	start: params.limit_start as number,
	pageLength: params.limit_page_length as number,
});

/**
 * The five URLs `createListResource` and `createDocumentResource` reach for.
 *
 * They are Frappe's own names because that is what the resources send, and
 * `defaultListUrl` and its siblings default to exactly these strings.
 */
const ROUTES: Record<string, (params: Params) => Promise<unknown>> = {
	"frappe.client.get_list": (params) => {
		// a child table is read through its parent's permission, so a grant on the
		// child doctype would be answering a question nobody asked
		if (params.parent) {
			throw refuse("\"parent\" is not supported: grant the parent doctype instead.");
		}
		return data.getList(named(params, "doctype", "frappe.client.get_list"), listOptions(params));
	},

	"frappe.client.get_count": (params) =>
		data.getCount(
			named(params, "doctype", "frappe.client.get_count"),
			params.filters as ListOptions["filters"],
		),

	"frappe.client.get": (params) =>
		data.getDoc(
			named(params, "doctype", "frappe.client.get"),
			named(params, "name", "frappe.client.get"),
		),

	// the doctype travels inside the document here, not beside it
	"frappe.client.insert": (params) => {
		const doc = asParams(params.doc);
		return data.insert(named(doc, "doctype", "frappe.client.insert"), doc);
	},

	"frappe.client.set_value": (params) =>
		data.update(
			named(params, "doctype", "frappe.client.set_value"),
			named(params, "name", "frappe.client.set_value"),
			patchOf(params),
		),

	"frappe.client.delete": (params) =>
		data.delete(
			named(params, "doctype", "frappe.client.delete"),
			named(params, "name", "frappe.client.delete"),
		),
};

/**
 * Hand this to `setConfig("resourceFetcher", ...)`.
 *
 * It answers with the data, and throws on a refusal, which is the contract
 * `resources.js` expects. A refusal keeps its `code`, so a resource's `onError`
 * can still read `grant_required` and call `builder.data.requestAccess`. Read
 * the answer it returns: a denied access returns "denied" without a dialog.
 *
 * It never opens the consent dialog itself. A resource fetches when it decides
 * to — `auto: true` fires on mount — so an asking fetcher would put a modal on
 * screen while the user is doing something else.
 */
export const resourceFetcher = (options: ResourceRequest) => {
	const url = options?.url ?? "";
	const route = ROUTES[url];

	if (!route) {
		throw refuse(
			`no route for "${url}". An extension reaches site data through a doctype it was ` +
				`granted, so a resource may name only: ${Object.keys(ROUTES).join(", ")}.`,
		);
	}

	return route(asParams(options.params));
};
