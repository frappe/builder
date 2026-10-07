/**
 * Reads, adds, changes and removes real documents.
 *
 * Each method starts with the same gate. The `data.access` permission says
 * that this extension can use site data.
 *
 * The second gate is the most important, and no code here can change it.
 * `frappe.client` runs the query as the logged-in user. So an extension sees
 * only the rows that this user sees.
 *
 * The option names come from `createListResource`: `fields`, `filters`,
 * `orderBy`, `start` and `pageLength`. An extension author writes frontend
 * code, and this repo already uses these names. The host changes them to the
 * Frappe names before it sends the request.
 *
 * These are not page writes. So read-only mode does not refuse them.
 * Read-only mode is about the open page, and a Contact is not that page.
 */

import { createResource } from "frappe-ui";
import type { MethodTable } from "../bridge/permissions";
import { fields, optionalText, refuse, text, wholeNumber } from "../bridge/params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

/**
 * Makes a value that `postMessage` can always clone.
 *
 * `createResource` keeps its `data` reactive, and `postMessage` cannot clone a
 * Vue proxy. A document has no fixed shape, so this code cannot copy it field
 * by field. A JSON round trip makes it plain. It removes `undefined`, but a
 * document from the server never has `undefined`.
 */
const plain = <T>(value: T): T => JSON.parse(JSON.stringify(value ?? null));

/** A server refusal, in a form that the frame can act on. A second call does not change it. */
const asRefusal = (thrown: unknown) => {
	const sent = thrown as { exc_type?: string; messages?: string[]; message?: string };
	const message = sent.messages?.[0] || sent.message || "The server refused that call.";
	return refuse(message, "server_error");
};

/** One call, as `tokenMethods.ts` calls a whitelisted method. */
const invoke = (url: string, params: Record<string, unknown>) =>
	createResource({ url })
		.submit(params)
		.then(plain)
		.catch((thrown: unknown) => {
			throw asRefusal(thrown);
		});

const readDoctype = (sent: Record<string, unknown>) => text(sent.doctype, "doctype");

const readName = (sent: Record<string, unknown>) => text(sent.name, "name");

/** A patch or a new document. Never a list, and never a single value. */
const readDoc = (value: unknown) => {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		throw refuse('"doc" must be an object.', "invalid_params");
	}
	return value as Record<string, unknown>;
};

/**
 * A dict of equal values, or the Frappe list form for other filters. This code
 * does not parse the filter. The query builder reads it. A second reader here
 * would be a second rule to keep the same.
 */
const readFilters = (value: unknown) => {
	if (value === undefined) return undefined;
	if (typeof value !== "object" || value === null) {
		throw refuse("A filter must be an object or a list.", "invalid_params");
	}
	return value;
};

const readFields = (value: unknown) => {
	if (value === undefined) return undefined;
	if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
		throw refuse('"fields" must be a list of field names.', "invalid_params");
	}
	return value as string[];
};

const optionalCount = (value: unknown, field: string) =>
	value === undefined ? undefined : wholeNumber(value, field);

const getList = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.data.get_list", {
		extension: extension.name,
		doctype: readDoctype(sent),
		fields: readFields(sent.fields),
		filters: readFilters(sent.filters),
		or_filters: readFilters(sent.orFilters),
		order_by: optionalText(sent.orderBy, "orderBy"),
		group_by: optionalText(sent.groupBy, "groupBy"),
		limit_start: optionalCount(sent.start, "start"),
		// not set here when missing. The server owns the page size rule
		limit_page_length: optionalCount(sent.pageLength, "pageLength"),
	});
};

const getCount = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.data.get_count", {
		extension: extension.name,
		doctype: readDoctype(sent),
		filters: readFilters(sent.filters),
	});
};

const getDoc = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.data.get_doc", {
		extension: extension.name,
		doctype: readDoctype(sent),
		name: readName(sent),
	});
};

const insert = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.data.insert_doc", {
		extension: extension.name,
		doctype: readDoctype(sent),
		doc: readDoc(sent.doc),
	});
};

const update = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.data.update_doc", {
		extension: extension.name,
		doctype: readDoctype(sent),
		name: readName(sent),
		doc: readDoc(sent.doc),
	});
};

const remove = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.data.delete_doc", {
		extension: extension.name,
		doctype: readDoctype(sent),
		name: readName(sent),
	});
};

export const documentMethods: MethodTable = {
	"data.getList": { needs: "data.access", run: getList },
	"data.getCount": { needs: "data.access", run: getCount },
	"data.getDoc": { needs: "data.access", run: getDoc },
	"data.insert": { needs: "data.access", run: insert },
	"data.update": { needs: "data.access", run: update },
	"data.delete": { needs: "data.access", run: remove },
};
