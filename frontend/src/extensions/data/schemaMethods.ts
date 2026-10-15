/**
 * The doctypes that an extension makes while the editor runs.
 */

import type { MethodTable } from "../bridge/permissions";
import { fields, flag, oneOf, refuse, text } from "../bridge/params";
import { confirmSchema, type AccessChange } from "./confirmations";
import { invoke } from "./documentMethods";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

const NAMING = ["hash", "autoincrement", "prompt"] as const;

/**
 * A field list. This code checks only its shape. The server decides which
 * field types are allowed. So there is one list, not two lists that can differ.
 */
const readFields = (value: unknown, allowEmpty = false) => {
	if (!Array.isArray(value) || (!value.length && !allowEmpty)) {
		throw refuse('"fields" must be a non-empty list.', "invalid_params");
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

/** Omitted fields stay. Explicit removals require a host confirmation. */
const updateDoctype = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const doctype = text(sent.doctype, "doctype");
	const removed = readRemovedFields(sent.removeFields);
	const rows = readFields(sent.fields, removed.length > 0);
	if (
		removed.length &&
		!(await confirmSchema(extension, doctype, "remove field", { detail: removed.join(", ") }))
	) {
		throw refuse(`The user did not allow removing fields from ${doctype}.`, "refused");
	}
	return invoke("builder.extensions.schema.update_doctype", {
		extension: extension.name,
		doctype,
		fields: rows,
		remove_fields: removed,
	});
};

const readRemovedFields = (value: unknown): string[] => {
	if (value === undefined) return [];
	if (!Array.isArray(value)) throw refuse('"removeFields" must be a list of field names.', "invalid_params");
	return value.map((name) => text(name, "removeFields"));
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

/**
 * Asks first, with the change that the server computes, then sets who can use a
 * doctype that this extension made. The server writes only that approved change.
 */
const setAccess = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const request = {
		extension: extension.name,
		doctype: text(sent.doctype, "doctype"),
		roles: readRoles(sent.roles),
	};
	const access = (await invoke("builder.extensions.schema.get_access_change", request)) as AccessChange;
	const isChanged = access.added.length > 0 || access.removed.length > 0;
	if (isChanged && !(await confirmSchema(extension, request.doctype, "change access", { access }))) {
		throw refuse(`The user did not allow changing who can use ${request.doctype}.`, "refused");
	}
	return invoke("builder.extensions.schema.set_doctype_access", { ...request, access });
};

const readRoles = (value: unknown): string[] => {
	if (!Array.isArray(value)) throw refuse('"roles" must be a list of role names.', "invalid_params");
	return value.map((role) => text(role, "roles"));
};

const listRoles = (_params: unknown, extension: InstalledExtension) =>
	invoke("builder.extensions.schema.list_roles", { extension: extension.name });

const listDoctypes = (_params: unknown, extension: InstalledExtension) =>
	invoke("builder.extensions.schema.list_doctypes", { extension: extension.name });

export const schemaMethods: MethodTable = {
	"schema.createDoctype": { needs: "schema.write", run: createDoctype },
	"schema.getDoctype": { needs: "schema.write", run: getDoctype },
	"schema.updateDoctype": { needs: "schema.write", run: updateDoctype },
	"schema.deleteDoctype": { needs: "schema.write", run: deleteDoctype },
	"schema.listDoctypes": { needs: "schema.write", run: listDoctypes },
	"schema.setAccess": { needs: "schema.write", run: setAccess },
	"schema.listRoles": { needs: "schema.write", run: listRoles },
};
