import { __ } from "@/translation";
import type { EditorDemoPayload } from "@/utils/editorDemo";

type Doc = Record<string, any>;

// lookups the editor makes that the demo answers the same way every time
const STUBS: Record<string, unknown> = {
	"frappe.client.has_permission": { has_permission: true },
	"builder.api.get_component_data": {},
	"builder.api.get_template_groups": [],
	"builder.api.get_codemirror_completions": [],
	"builder.api.is_site_read_only": false,
	"builder.ai.api.ai_setup_state": { configured: false },
	"builder.ai.api.get_ai_models": [],
	"builder.ai.api.get_ai_session": null,
	"builder.ai.api.list_page_ai_sessions": [],
};

// the page methods the editor only reads through; every other one would save or publish
const PAGE_READS: Record<string, unknown> = {
	get_page_data: {},
	get_outdated_component_pins: [],
	get_current_component_version: null,
};

// rejects the way frappeRequest does, so callers' error handling stays unchanged
function refuse(message = __("Only this page can change in the demo, and nothing is saved")): never {
	throw Object.assign(new Error(message), { messages: [message] });
}

/**
 * Stands in for the server while the editor runs as a demo: an in-memory copy of the page
 * and what it renders with. Visitors change the page, never what the rest of the site shares.
 */
export function createEditorDemoBackend(payload: EditorDemoPayload) {
	const docs: Record<string, Doc[]> = {
		"Builder Page": [payload.page],
		"Builder Component": Object.values(payload.components),
		"Builder Token": payload.tokens,
		"User Font": payload.fonts,
		"Block Template": payload.blockTemplates,
		// the demo should behave like the live page, and these scripts are the page's own
		"Builder Settings": [{ name: "Builder Settings", execute_block_scripts_in_editor: "Unrestricted" }],
		"Website Settings": [{ name: "Website Settings" }],
	};
	const find = (doctype: string, name: string) =>
		docs[doctype]?.find((doc) => doc.name === name) ?? refuse(__("{0} {1} not found", [doctype, name]));

	const methods: Record<string, (params: Doc) => unknown> = {
		"frappe.client.get": ({ doctype, name }) => find(doctype, name),
		// one page in memory, so list filters would not change what the editor gets back
		"frappe.client.get_list": ({ doctype, fields }) =>
			(docs[doctype] || []).map((doc) =>
				Array.isArray(fields) && !fields.includes("*")
					? Object.fromEntries(fields.map((field) => [field, doc[field]]))
					: doc,
			),
		"frappe.client.set_value": ({ doctype, name, fieldname, value }) => {
			const values = typeof fieldname === "string" ? { [fieldname]: value } : fieldname;
			const isPage = doctype === "Builder Page" && name === payload.page.name;
			if (!isPage || "published" in values || "staging" in values) refuse();
			return Object.assign(find(doctype, name), values);
		},
		run_doc_method: ({ method }) =>
			method in PAGE_READS ? { message: PAGE_READS[method], docs: [] } : refuse(),
		"builder.api.get_versioned_doc": ({ snapshot }) =>
			payload.componentVersions[snapshot] ?? refuse(__("Version not found")),
	};

	return async ({ url, params }: { url: string; params?: Doc }) => {
		const method = url.replace(/^\/api\/method\//, "");
		if (method in STUBS) return structuredClone(STUBS[method]);
		if (!methods[method]) refuse();
		return structuredClone(methods[method](params || {}));
	};
}
