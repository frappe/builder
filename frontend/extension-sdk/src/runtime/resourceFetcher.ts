/**
 * Sends frappe-ui resource requests through the bridge.
 *
 * An extension frame has an opaque origin and no cookie. So `fetch` cannot
 * reach Frappe from the frame. `createResource` reads its fetcher on each
 * request. So one `setConfig` call sends each resource in the frame through
 * the port:
 *
 * ```js
 * import { setConfig } from "frappe-ui";
 * import builder from "frappe-builder-extension-sdk";
 *
 * setConfig("resourceFetcher", builder.data.fetcher);
 * ```
 *
 * Write it in the entry, which each frame imports. Use the `frappe-ui` of the
 * extension. Each extension bundles its own copy, and the SDK cannot reach the
 * config of that copy.
 *
 * **This is an adapter, not a gate.** It runs in the frame, and the frame is
 * not trusted. So it decides nothing. Each route below goes to a `data.*`
 * method. The host gates that method, and the server checks the permission.
 * A frame that replaces this file gets the same methods and the same refusals.
 *
 * The adapter refuses a URL with no route. It does not forward it. If it did,
 * a resource could call any whitelisted method on the site. Then the
 * `data.access` permission would have no effect.
 */

import { ChannelCallError } from "../shared/transport/createPortChannel";
import { data, type ListOptions } from "./namespaces";

type Params = Record<string, unknown>;

/** frappe-ui gives the fetcher all the resource options, with the params resolved. */
export type ResourceRequest = { url?: string; params?: Params };

const refuse = (message: string, code = "unsupported_request") =>
	new ChannelCallError({ message: `[builder] ${message}`, code });

/**
 * A plain deep copy of the data that a resource sent.
 *
 * `createListResource` keeps its state in a `reactive`. `makeParams` gives those
 * values directly to the fetcher. For example, `out.fields` is a proxy of an
 * array, and `out.filters` is a proxy of an object.
 *
 * `postMessage` cannot clone a proxy. So this code makes plain copies before
 * the send. The host makes a plain copy of the answer for the same reason.
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
 * `set_value` sends its patch as `fieldname`. From frappe-ui, it is always an
 * object. A hand-written `createResource` sends one field, as `fieldname` and
 * `value`. So this code reads both forms.
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
 * The five URLs that `createListResource` and `createDocumentResource` use.
 *
 * They are the Frappe names, because the resources send these names.
 * `defaultListUrl` and the related settings use these strings by default.
 */
const ROUTES: Record<string, (params: Params) => Promise<unknown>> = {
	"frappe.client.get_list": (params) => {
		// the permission of the parent controls a child table. So read the parent
		if (params.parent) {
			throw refuse("\"parent\" is not supported: read the parent document instead.");
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

	// here, the doctype is inside the document, not next to it
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
 * Give this to `setConfig("resourceFetcher", ...)`.
 *
 * It returns the data, and it throws an error on a refusal. `resources.js`
 * expects this. A refusal keeps its `code`. So the `onError` of a resource can
 * read it.
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
