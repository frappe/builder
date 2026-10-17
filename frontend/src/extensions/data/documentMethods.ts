/**
 * Reads, adds, changes and removes real documents.
 */

import { createResource, FileUploadHandler } from "frappe-ui";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import { fields, optionalText, refuse, text, wholeNumber } from "../bridge/params";
import { refreshEditor } from "./editorRefresh";
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

export const invoke = (url: string, params: Record<string, unknown>) =>
	createResource({ url })
		.submit(params)
		.then(plain)
		.catch((thrown: unknown) => {
			throw asRefusal(thrown);
		});

const readDoctype = (sent: Record<string, unknown>) => text(sent.doctype, "doctype");

const readName = (sent: Record<string, unknown>) => text(sent.name, "name");

const notifyChange = (
	extension: InstalledExtension,
	doctype: string,
	name: string,
	operation: "insert" | "update" | "delete",
) =>
	bridge
		.getChannels(extension.name)
		.forEach((channel) => channel.emit("data.changed", { doctype, name, operation }));

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

/** The call answers after the editor reloads its copy. So the extension never reads a stale editor. */
const insert = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const doctype = readDoctype(sent);
	const doc = await invoke("builder.extensions.data.insert_doc", {
		extension: extension.name,
		doctype,
		doc: readDoc(sent.doc),
	});
	await refreshEditor(doctype, doc.name, "insert");
	notifyChange(extension, doctype, doc.name, "insert");
	return doc;
};

const update = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const doctype = readDoctype(sent);
	const name = readName(sent);
	const doc = await invoke("builder.extensions.data.update_doc", {
		extension: extension.name,
		doctype,
		name,
		doc: readDoc(sent.doc),
	});
	await refreshEditor(doctype, name, "update");
	notifyChange(extension, doctype, name, "update");
	return doc;
};

const remove = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const doctype = readDoctype(sent);
	const name = readName(sent);
	await invoke("builder.extensions.data.delete_doc", { extension: extension.name, doctype, name });
	await refreshEditor(doctype, name, "delete");
	notifyChange(extension, doctype, name, "delete");
};

/** A `File` crosses the port as a clone, so it is a real `File` here. */
const readFile = (value: unknown) => {
	if (!(value instanceof File)) throw refuse('"file" must be a File.', "invalid_params");
	return value;
};

/** The frame has no session at its opaque origin, so the host posts the file. */
const uploadFile = async (params: unknown, extension: InstalledExtension) => {
	const file = readFile(fields(params).file);
	const endpoint = `/api/method/builder.extensions.data.upload_file?extension=${encodeURIComponent(extension.name)}`;
	const uploaded = await new FileUploadHandler()
		.upload(file, { private: false, folder: "Home/Builder Uploads", upload_endpoint: endpoint })
		.catch((thrown: unknown) => {
			throw asRefusal(thrown);
		});
	return { fileUrl: uploaded.file_url, fileName: uploaded.file_name };
};

export const documentMethods: MethodTable = {
	"data.getList": { needs: "data.access", run: getList },
	"data.getCount": { needs: "data.access", run: getCount },
	"data.getDoc": { needs: "data.access", run: getDoc },
	"data.insert": { needs: "data.access", run: insert },
	"data.update": { needs: "data.access", run: update },
	"data.delete": { needs: "data.access", run: remove },
	"data.uploadFile": { needs: "data.access", run: uploadFile },
};
