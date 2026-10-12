/** `builder.schema`: the doctypes that this extension makes. */

import { call } from "./call";

/** One field of a doctype that an extension makes. */
export type SchemaField = {
	fieldname?: string;
	label?: string;
	/** A layout break and a Heading need no fieldname. A Table needs a child doctype, so it is not allowed. */
	fieldtype: string;
	/** The linked doctype for a Link. For a Select, the choices, one on each line. */
	options?: string;
	reqd?: boolean;
	unique?: boolean;
	default?: unknown;
	in_list_view?: boolean;
	read_only?: boolean;
	description?: string;
};

export type Doctype = {
	doctype: string;
	istable: boolean;
	fields: SchemaField[];
};

/** How a new document gets its name. It is set at creation. A later change renames nothing. */
export type Naming = "hash" | "autoincrement" | "prompt";

export const schema = {
	/**
	 * Makes a new custom doctype. This extension owns it.
	 *
	 * Builder first asks the user, with the name. If the user says no, the call
	 * fails with the code `refused`. It needs the `schema.write` permission. The
	 * **user** must also be a System Manager. Frappe needs create permission on
	 * `DocType`, and nothing here changes that.
	 */
	createDoctype: (
		doctype: string,
		fields: SchemaField[],
		options: { naming?: Naming; istable?: boolean } = {},
	) => call("schema.createDoctype", { doctype, fields, ...options }) as Promise<Doctype>,

	/** The field list of a doctype that the user can read. */
	getDoctype: (doctype: string) => call("schema.getDoctype", { doctype }) as Promise<Doctype>,

	/**
	 * Adds fields, and changes the existing fields by fieldname.
	 *
	 * It never removes a field that the call does not name. A removed field
	 * removes a column and its data. Only the extension that made the doctype
	 * can call this.
	 */
	updateDoctype: (doctype: string, fields: SchemaField[]) =>
		call("schema.updateDoctype", { doctype, fields }) as Promise<Doctype>,

	/** Removes a doctype that this extension made, and its table. Builder asks the user first. */
	deleteDoctype: (doctype: string) => call("schema.deleteDoctype", { doctype }),

	/** Each doctype that this extension made, and if it still exists. */
	listDoctypes: () => call("schema.listDoctypes") as Promise<Array<{ doctype: string; exists: boolean }>>,
};
