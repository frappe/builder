/**
 * frappe-ui's requests, read on the trusted side.
 *
 * The SDK wraps the frame's `fetch` and sends every `/api/method/*` and
 * `/api/v2/*` request here unread. This file decides which operation a request
 * is and hands it to the host method that already gates that operation, so a
 * request reaches exactly what the matching SDK call reaches.
 *
 * Each route names its own permission: a document request needs `data.access`,
 * and any other method needs `method.call`. The server refuses every method of
 * `frappe` and `builder`, and `frappe.client.*` is read here as the CRUD it is,
 * never as a method, so `method.call` never stands in for `data.access`.
 */

import type { ApiAnswer, InstalledExtension, Permission } from "frappe-builder-extension-sdk/types";
import { fields, refuse, text, wholeNumber } from "../bridge/params";
import { assertGranted, type MethodTable } from "../bridge/permissions";
import { getCount, getDoc, getList, getMeta, insert, invoke, remove, update } from "./documentMethods";

type Params = Record<string, unknown>;

/** One request, parsed. `params` merges the query and the body, the way Frappe's `form_dict` does. */
type ApiCall = { verb: string; path: string[]; params: Params };

type Route = (call: ApiCall, extension: InstalledExtension) => Promise<ApiAnswer>;

/** A route and the permission it needs. */
type GatedRoute = { needs: Permission; run: Route };

const dataRoute = (run: Route): GatedRoute => ({ needs: "data.access", run });

const methodRoute = (run: Route): GatedRoute => ({ needs: "method.call", run });

/** Frappe's own page size when a v2 list names none. */
const V2_PAGE_LENGTH = 20;

const readBody = (body: unknown): Params => {
	if (body === undefined) return {};
	try {
		const parsed = JSON.parse(text(body, "body"));
		if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) return parsed;
	} catch {
		// refused below, with the same message as a body that parsed to a list
	}
	throw refuse("A request body must be a JSON object.", "invalid_params");
};

/** A query string cannot say "no value", so frappe-ui leaves out a null and may send an empty string. */
const withoutEmpty = (params: Params) =>
	Object.fromEntries(Object.entries(params).filter(([, value]) => value !== null && value !== ""));

/** Split before decoding, so a name holding an encoded slash stays one segment. */
const readCall = (params: unknown): ApiCall => {
	const sent = fields(params);
	const url = new URL(text(sent.url, "url"), "http://frame.invalid");
	return {
		verb: text(sent.method, "method").toUpperCase(),
		path: url.pathname.split("/").filter(Boolean).map(decodeURIComponent),
		params: { ...withoutEmpty(Object.fromEntries(url.searchParams)), ...readBody(sent.body) },
	};
};

/** A query string carries a list or a dict as JSON text. A body carries it as itself. */
const decoded = (value: unknown) => {
	if (typeof value !== "string") return value;
	try {
		return JSON.parse(value);
	} catch {
		return value;
	}
};

/** A query string carries a number as text. Anything else reaches the validator as it came. */
const number = (value: unknown) => (typeof value === "string" && /^\d+$/.test(value) ? Number(value) : value);

const answer = (result: Promise<unknown>): Promise<ApiAnswer> => result.then((data) => ({ data }));

const unsupported = (call: ApiCall) =>
	refuse(
		`No route for ${call.verb} /${call.path.join("/")}. An extension reaches site data ` +
			`through a doctype it was granted.`,
		"unsupported_request",
	);

/** A child table is read through its parent's permission, so a grant on the child would answer nothing. */
const refuseParent = (params: Params) => {
	if (params.parent) {
		throw refuse('"parent" is not supported: grant the parent doctype instead.', "unsupported_request");
	}
};

const listOptions = (params: Params, doctype: unknown) => {
	refuseParent(params);
	return {
		doctype,
		fields: decoded(params.fields),
		filters: decoded(params.filters),
		orFilters: decoded(params.or_filters),
		orderBy: params.order_by,
		groupBy: params.group_by,
	};
};

/**
 * `set_value` carries its patch as `fieldname`, which is an object from every
 * frappe-ui path. The one-field form, `fieldname` plus `value`, is what a
 * hand-written call sends, so both are read here.
 */
const patchOf = (params: Params) => {
	const sent = decoded(params.fieldname);
	return typeof sent === "string" ? { [sent]: params.value } : sent;
};

const CLIENT_ROUTES: Record<string, Route> = {
	"frappe.client.get_list": ({ params }, extension) =>
		answer(
			getList(
				{
					...listOptions(params, params.doctype),
					start: number(params.limit_start),
					pageLength: number(params.limit_page_length),
				},
				extension,
			),
		),

	"frappe.client.get_count": ({ params }, extension) =>
		answer(getCount({ doctype: params.doctype, filters: decoded(params.filters) }, extension)),

	"frappe.client.get": ({ params }, extension) =>
		answer(getDoc({ doctype: params.doctype, name: params.name }, extension)),

	// the doctype travels inside the document here, not beside it
	"frappe.client.insert": ({ params }, extension) => {
		const doc = decoded(params.doc);
		return answer(insert({ doctype: fields(doc).doctype, doc }, extension));
	},

	"frappe.client.set_value": ({ params }, extension) =>
		answer(update({ doctype: params.doctype, name: params.name, doc: patchOf(params) }, extension)),

	"frappe.client.delete": ({ params }, extension) =>
		answer(remove({ doctype: params.doctype, name: params.name }, extension)),
};

/**
 * v2 pages by `has_next_page`, which Frappe answers by fetching one row more
 * than the page. The server's ceiling applies to that larger number, so a v2
 * page holds at most one row less than a v1 page.
 */
const listPage = async ({ params }: ApiCall, doctype: string, extension: InstalledExtension) => {
	const limit = wholeNumber(number(params.limit ?? V2_PAGE_LENGTH), "limit");
	const options = { ...listOptions(params, doctype), start: number(params.start), pageLength: limit + 1 };
	const rows = (await getList(options, extension)) as unknown[];
	return { data: rows.slice(0, limit), hasNextPage: rows.length > limit };
};

type DocumentRoute = (
	call: ApiCall,
	doctype: string,
	name: string,
	extension: InstalledExtension,
) => Promise<ApiAnswer>;

const V2_LIST_ROUTES: Record<string, DocumentRoute> = {
	GET: (call, doctype, _name, extension) => listPage(call, doctype, extension),
	POST: ({ params }, doctype, _name, extension) => answer(insert({ doctype, doc: params }, extension)),
};

const updateDocument: DocumentRoute = ({ params }, doctype, name, extension) =>
	answer(update({ doctype, name, doc: params }, extension));

const V2_DOCUMENT_ROUTES: Record<string, DocumentRoute> = {
	GET: (_call, doctype, name, extension) => answer(getDoc({ doctype, name }, extension)),
	PUT: updateDocument,
	PATCH: updateDocument,
	// Frappe answers a v2 delete with "ok", and a client may compare against it
	DELETE: (_call, doctype, name, extension) =>
		remove({ doctype, name }, extension).then(() => ({ data: "ok" })),
};

const V2_DOCTYPE_ROUTES: Record<string, Route> = {
	count: ({ params, path }, extension) =>
		answer(getCount({ doctype: path[3], filters: decoded(params.filters) }, extension)),
	meta: ({ path }, extension) => answer(getMeta({ doctype: path[3] }, extension)),
};

/** A module method, or a function in a doctype's controller module. */
const runMethod = (extension: InstalledExtension, method: string, verb: string, args: unknown) =>
	invoke("builder.extensions.methods.run_method", { extension: extension.name, method, verb, args });

/** Answers `{ message, docs }`: frappe-ui's document resource reads the refreshed document from `docs`. */
const runDocMethod = (extension: InstalledExtension, target: Params, verb: string, args: unknown) =>
	invoke("builder.extensions.methods.run_doc_method", {
		extension: extension.name,
		...target,
		verb,
		args,
	}) as Promise<{ message: unknown; docs: unknown[] }>;

const moduleMethod = (method: string) =>
	methodRoute((call, extension) => answer(runMethod(extension, method, call.verb, call.params)));

const docMethod = (target: Params, args: unknown) =>
	methodRoute((call, extension) =>
		runDocMethod(extension, target, call.verb, args ?? {}).then(({ message, docs }) => ({
			data: message,
			docs,
		})),
	);

/** v1 sends `dt`, `dn` and `args`. The older form that sends the whole document is refused. */
const version1DocMethod = ({ params }: ApiCall) =>
	docMethod({ doctype: params.dt, name: params.dn, method: params.method }, decoded(params.args));

const findVersion1Route = (call: ApiCall, method: string): GatedRoute => {
	if (CLIENT_ROUTES[method]) return dataRoute(CLIENT_ROUTES[method]);
	if (method === "run_doc_method") return version1DocMethod(call);
	return moduleMethod(method);
};

/** `/document/<doctype>/<name>/method/<method>`. A name may hold slashes, so the method is read from the end. */
const findDocumentRoute = (call: ApiCall, doctype: string, rest: string[]): GatedRoute | undefined => {
	const last = rest.length - 1;
	if (last >= 2 && rest[last - 1] === "method") {
		return docMethod({ doctype, name: rest.slice(0, -2).join("/"), method: rest[last] }, call.params);
	}
	// `bulk_*` needs no case of its own: it is a POST, and one named document takes none
	if (rest.length > 1 && rest[last] === "copy") return undefined;

	const route = (rest.length ? V2_DOCUMENT_ROUTES : V2_LIST_ROUTES)[call.verb];
	return route && dataRoute((sent, extension) => route(sent, doctype, rest.join("/"), extension));
};

/** `/method/<dotted.path>`, or `/method/<doctype>/<method>`: both join to the name the server reads. */
const findVersion2Route = (call: ApiCall, [resource, ...rest]: string[]) => {
	if (resource === "method" && (rest.length === 1 || rest.length === 2)) return moduleMethod(rest.join("."));
	if (resource === "document" && rest.length) return findDocumentRoute(call, rest[0], rest.slice(1));

	const doctypeRoute = resource === "doctype" && rest.length === 2 && V2_DOCTYPE_ROUTES[rest[1]];
	return doctypeRoute && call.verb === "GET" ? dataRoute(doctypeRoute) : undefined;
};

const findRoute = (call: ApiCall): GatedRoute | undefined => {
	const [api, family, ...rest] = call.path;
	if (api !== "api") return undefined;
	if (family === "v2") return findVersion2Route(call, rest);
	return family === "method" && rest.length ? findVersion1Route(call, rest.join("/")) : undefined;
};

/** Gated per route rather than per method, because one request method reaches both data and code. */
const request = (params: unknown, extension: InstalledExtension) => {
	const call = readCall(params);
	const route = findRoute(call);
	if (!route) throw unsupported(call);

	assertGranted(extension, "data.request", route.needs);
	return route.run(call, extension);
};

export const requestMethods: MethodTable = {
	"data.request": { needs: null, run: request },
};
