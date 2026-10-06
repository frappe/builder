/**
 * The doctypes that an extension makes while the editor runs.
 *
 * There are three gates:
 * 1. `schema.write` says that a manager let this extension make tables.
 * 2. A confirmation names the doctype when the extension makes or removes it.
 * 3. Frappe needs create permission on `DocType`, which a System Manager has.
 *    So the call fails for a page editor, and that is correct.
 *
 * A record shows the owner, not a naming rule. Only the extension that made a
 * doctype can change or remove it. `data.access` is not sufficient, because
 * to read a table is not the same as to change its shape.
 *
 * These are not page writes. So read-only mode does not refuse them. A table
 * is not the open page.
 */

import { createResource } from "frappe-ui";
import type { MethodTable } from "../bridge/permissions";
import { fields, flag, oneOf, refuse, text } from "../bridge/params";
import { confirmSchema } from "./confirmations";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

const NAMING = ["hash", "autoincrement", "prompt"] as const;

/** A plain copy, because `createResource` returns its reactive `data`. */
const plain = <T>(value: T): T => JSON.parse(JSON.stringify(value ?? null));

const asRefusal = (thrown: unknown) => {
	const sent = thrown as { messages?: string[]; message?: string };
	return refuse(sent.messages?.[0] || sent.message || "The server refused that call.", "server_error");
};

const invoke = (url: string, params: Record<string, unknown>) =>
	createResource({ url })
		.submit(params)
		.then(plain)
		.catch((thrown: unknown) => {
			throw asRefusal(thrown);
		});

/**
 * A field list. This code checks only its shape. The server decides which
 * field types are allowed. So there is one list, not two lists that can differ.
 */
const readFields = (value: unknown) => {
	if (!Array.isArray(value) || !value.length) {
		throw refuse("\"fields\" must be a non-empty list.", "invalid_params");
	}
	return value.map((field) => {
		if (!field || typeof field !== "object" || Array.isArray(field)) {
			throw refuse("Every field must be an object.", "invalid_params");
		}
		return field as Record<string, unknown>;
	});
};

/**
 * Asks first, then makes the doctype. The user answers before any write. So a
 * refusal leaves no part of a table.
 */
const createDoctype = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const doctype = text(sent.doctype, "doctype");
	const rows = readFields(sent.fields);
	const naming = sent.naming === undefined ? "hash" : oneOf(sent.naming, NAMING, "naming");

	if (!(await confirmSchema(extension, doctype, "create"))) {
		throw refuse(`The user did not allow "${extension.name}" to create ${doctype}.`, "refused");
	}

	return invoke("builder.extensions.schema.create_doctype", {
		extension: extension.name,
		doctype,
		fields: rows,
		naming,
		istable: flag(sent.istable, false),
	});
};

const getDoctype = (params: unknown, extension: InstalledExtension) =>
	invoke("builder.extensions.schema.get_doctype", {
		extension: extension.name,
		doctype: text(fields(params).doctype, "doctype"),
	});

/** Adds fields and changes them by fieldname. It never removes a field, so no column is removed. */
const updateDoctype = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invoke("builder.extensions.schema.update_doctype", {
		extension: extension.name,
		doctype: text(sent.doctype, "doctype"),
		fields: readFields(sent.fields),
	});
};

const deleteDoctype = async (params: unknown, extension: InstalledExtension) => {
	const doctype = text(fields(params).doctype, "doctype");

	if (!(await confirmSchema(extension, doctype, "delete"))) {
		throw refuse(`The user did not allow "${extension.name}" to delete ${doctype}.`, "refused");
	}

	return invoke("builder.extensions.schema.delete_doctype", {
		extension: extension.name,
		doctype,
	});
};

const listDoctypes = (_params: unknown, extension: InstalledExtension) =>
	invoke("builder.extensions.schema.list_doctypes", { extension: extension.name });

export const schemaMethods: MethodTable = {
	"schema.createDoctype": { needs: "schema.write", run: createDoctype },
	"schema.getDoctype": { needs: "schema.write", run: getDoctype },
	"schema.updateDoctype": { needs: "schema.write", run: updateDoctype },
	"schema.deleteDoctype": { needs: "schema.write", run: deleteDoctype },
	"schema.listDoctypes": { needs: "schema.write", run: listDoctypes },
};
