import { __ } from "@/translation";
import type { EditorDemoPayload } from "@/utils/editorDemo";

type Doc = Record<string, any>;
type Params = Record<string, any>;
type Filter = [string, string, unknown];

/** Rejects like frappeRequest does, so callers' error handling stays unchanged. */
class EditorDemoError extends Error {
	exc_type = "EditorDemoError";
	messages: string[];
	constructor(message: string) {
		super(message);
		this.messages = [message];
	}
}

/**
 * Stands in for the server while the editor runs as a demo: an in-memory copy
 * of the page and what it renders with. Nothing here reaches the network.
 */
export class EditorDemoBackend {
	private docs = new Map<string, Map<string, Doc>>();
	private versions: EditorDemoPayload["componentVersions"];
	private pageName: string;

	constructor(payload: EditorDemoPayload) {
		this.add("Builder Page", [payload.page]);
		this.add("Builder Component", Object.values(payload.components));
		this.add("Builder Token", payload.tokens);
		this.add("User Font", payload.fonts);
		this.add("Block Template", payload.blockTemplates);
		// the demo should behave like the live page, and these scripts are the page's own
		this.add("Builder Settings", [
			{ name: "Builder Settings", execute_block_scripts_in_editor: "Unrestricted" },
		]);
		this.add("Website Settings", [{ name: "Website Settings" }]);
		this.versions = payload.componentVersions;
		this.pageName = payload.page.name;
	}

	private methods: Record<string, (params: Params) => unknown> = {
		"frappe.client.get": ({ doctype, name }) => this.get(doctype, name),
		"frappe.client.get_list": (params) => this.getList(params),
		"frappe.client.get_count": (params) => this.getList(params).length,
		"frappe.client.set_value": ({ doctype, name, fieldname, value }) =>
			this.setValue(doctype, name, typeof fieldname === "string" ? { [fieldname]: value } : fieldname),
		"frappe.client.insert": () => this.refuseSiteChange(),
		"frappe.client.delete": () => this.refuseSiteChange(),
		"frappe.client.has_permission": () => ({ has_permission: true }),
		run_doc_method: ({ method }) => this.runDocMethod(method),
		"builder.api.get_versioned_doc": ({ snapshot }) => this.getVersion(snapshot),
		"builder.api.get_component_data": () => ({}),
		"builder.api.get_template_groups": () => [],
		"builder.api.get_codemirror_completions": () => [],
		"builder.api.is_site_read_only": () => false,
		"builder.ai.api.ai_setup_state": () => ({ configured: false }),
		"builder.ai.api.get_ai_models": () => [],
		"builder.ai.api.get_ai_session": () => null,
		"builder.ai.api.list_page_ai_sessions": () => [],
	};

	fetch = async ({ url, params }: { url: string; params?: Params }) => {
		const method = this.methods[url.replace(/^\/api\/method\//, "")];
		if (!method) {
			throw new EditorDemoError(__("This is not available in the demo"));
		}
		return structuredClone(await method(params || {}));
	};

	private add(doctype: string, docs: Doc[]) {
		const table = this.table(doctype);
		docs.forEach((doc) => table.set(doc.name, { doctype, ...doc }));
	}

	private table(doctype: string) {
		if (!this.docs.has(doctype)) {
			this.docs.set(doctype, new Map());
		}
		return this.docs.get(doctype) as Map<string, Doc>;
	}

	private get(doctype: string, name: string) {
		const doc = this.table(doctype).get(name);
		if (!doc) {
			throw new EditorDemoError(__("{0} {1} not found", [doctype, name]));
		}
		return doc;
	}

	private getVersion(snapshot: string) {
		if (!this.versions[snapshot]) {
			throw new EditorDemoError(__("Version not found"));
		}
		return this.versions[snapshot];
	}

	private getList({ doctype, fields, filters, or_filters, limit }: Params) {
		const rows = Array.from(this.table(doctype).values())
			.filter((doc) => matchesAll(doc, toFilters(filters)))
			.filter((doc) => !or_filters || matchesAny(doc, toFilters(or_filters)));
		return rows.slice(0, limit || undefined).map((doc) => pick(doc, fields));
	}

	// visitors edit the page, never what the rest of the site shares (tokens, components, settings)
	private setValue(doctype: string, name: string, values: Doc) {
		if (doctype !== "Builder Page" || name !== this.pageName) {
			this.refuseSiteChange();
		}
		if ("published" in values || "staging" in values) {
			throw new EditorDemoError(__("This is a demo, so nothing gets published or saved"));
		}
		return Object.assign(this.get(doctype, name), values, { modified: now() });
	}

	private refuseSiteChange(): never {
		throw new EditorDemoError(__("The demo can change this page, but not site-wide settings"));
	}

	private runDocMethod(method: string) {
		const results: Record<string, unknown> = {
			get_page_data: {},
			get_outdated_component_pins: [],
			get_current_component_version: null,
		};
		if (!(method in results)) {
			throw new EditorDemoError(__("This is a demo, so nothing gets published or saved"));
		}
		return { message: results[method], docs: [] };
	}
}

function now() {
	return new Date().toISOString().replace("T", " ").replace("Z", "");
}

function pick(doc: Doc, fields?: string[] | string) {
	if (!Array.isArray(fields) || fields.includes("*")) {
		return doc;
	}
	return Object.fromEntries(fields.map((field) => [field, doc[field]]));
}

function toFilters(filters?: Params | unknown[]): Filter[] {
	if (!filters) return [];
	if (Array.isArray(filters)) {
		// [field, operator, value] or the long form with the doctype first
		return filters.map((filter) => (filter.length === 4 ? filter.slice(1) : filter) as Filter);
	}
	return Object.entries(filters).map(([field, value]) =>
		Array.isArray(value) ? [field, value[0], value[1]] : [field, "=", value],
	);
}

function matchesAll(doc: Doc, filters: Filter[]) {
	return filters.every((filter) => matches(doc, filter));
}

function matchesAny(doc: Doc, filters: Filter[]) {
	return !filters.length || filters.some((filter) => matches(doc, filter));
}

function matches(doc: Doc, [field, operator, expected]: Filter) {
	const value = doc[field];
	switch (operator.toLowerCase()) {
		case "=":
			return isSame(value, expected);
		case "!=":
			return !isSame(value, expected);
		case "in":
			return toList(expected).some((item) => isSame(value, item));
		case "not in":
			return !toList(expected).some((item) => isSame(value, item));
		case "is":
			return expected === "set" ? Boolean(value) : !value;
		case "like":
			return String(value ?? "")
				.toLowerCase()
				.includes(String(expected).replace(/%/g, "").toLowerCase());
		default:
			return true;
	}
}

// the server stores unset checks as 0 and unset text as null or ""
function isSame(value: unknown, expected: unknown) {
	if (typeof expected === "number" || typeof expected === "boolean") {
		return Boolean(value) === Boolean(expected);
	}
	return String(value ?? "") === String(expected ?? "");
}

function toList(value: unknown) {
	return Array.isArray(value) ? value : String(value).split(",");
}
