/** `builder.data`: the documents of the site. */

import { call } from "./call";
import { getChannel } from "../connect";

export type DataChange = { doctype: string; name: string; operation: "insert" | "update" | "delete" };

/** One document, as Frappe keeps it. Its fields are the fields of the doctype. */
export type Doc = Record<string, unknown>;

/**
 * The options of `data.getList`. They have the same names as in
 * `createListResource`, because an extension author writes frontend code.
 */
export type ListOptions = {
	fields?: string[];
	/** A dict of equal values, or the Frappe list form: `[["status", "!=", "Open"]]`. */
	filters?: Record<string, unknown> | unknown[];
	/** These match with OR. `filters` match with AND. */
	orFilters?: Record<string, unknown> | unknown[];
	orderBy?: string;
	groupBy?: string;
	start?: number;
	/** 500 or less. The server refuses 0, because Frappe reads 0 as all rows. */
	pageLength?: number;
};

export const data = {
	/** Watches this extension's writes across its frames. Returns a function that stops listening. */
	subscribe: (doctype: string, handler: (change: DataChange) => void) =>
		getChannel().listen("data.changed", (payload) => {
			const change = payload as DataChange;
			if (change.doctype === doctype) handler(change);
		}),

	/**
	 * One page of documents.
	 *
	 * Each call here needs the `data.access` permission. It runs as the user of
	 * the editor, and it reaches only the documents of that user. A refusal comes
	 * from the site. A second call does not change it.
	 *
	 * Design tokens and client scripts are documents too. Use the `Builder Token`
	 * and `Builder Client Script` doctypes.
	 */
	getList: (doctype: string, options: ListOptions = {}) =>
		call("data.getList", { doctype, ...options }) as Promise<Doc[]>,

	/** The number of documents that match. It does not get the documents. */
	getCount: (doctype: string, filters?: ListOptions["filters"]) =>
		call("data.getCount", { doctype, filters }) as Promise<number>,

	/** One full document, with its child tables. */
	getDoc: (doctype: string, name: string) => call("data.getDoc", { doctype, name }) as Promise<Doc>,

	/** The fields and settings of a doctype, as Frappe's `/api/v2/doctype/<doctype>/meta` gives them. */
	getMeta: (doctype: string) => call("data.getMeta", { doctype }) as Promise<Doc>,

	/** Adds a new document. Returns the new document. */
	insert: (doctype: string, doc: Doc) => call("data.insert", { doctype, doc }) as Promise<Doc>,

	/** Changes only the fields that `doc` names. Returns the saved document. */
	update: (doctype: string, name: string, doc: Doc) =>
		call("data.update", { doctype, name, doc }) as Promise<Doc>,

	delete: (doctype: string, name: string) => call("data.delete", { doctype, name }),

	/**
	 * Uploads one public file the way the editor uploads an image, and returns its
	 * site URL. A frame cannot post to the site itself, so the host sends it.
	 */
	uploadFile: async (file: File) => {
		// a picked file is readable only in this frame's process, so send its bytes, not the handle
		const copy = new File([await file.arrayBuffer()], file.name, { type: file.type });
		return call("data.uploadFile", { file: copy }) as Promise<UploadedFile>;
	},
};

export type UploadedFile = { fileUrl: string; fileName: string };
