import { ref, onMounted } from "vue";

const EXTERNAL_EDITOR_PORT_RANGE = { start: 59000, end: 59021 };

interface ExternalEditorStatus {
	active: boolean;
	extension: string;
	uriScheme: string;
	name: string;
}

interface OpenScriptRequest {
	site: string;
	doctype: string;
	docname: string;
	field?: string;
	blockId?: string;
	blockField?: "blockClientScript" | "blockDataScript";
}

const isExternalEditorActive = ref(false);
const externalEditorPort = ref<number | null>(null);
const externalEditorUriScheme = ref<string>("vscode");
const editorName = ref<string>("VS Code");

async function checkExternalEditorStatus(): Promise<void> {
	isExternalEditorActive.value = false;
	externalEditorPort.value = null;

	for (let port = EXTERNAL_EDITOR_PORT_RANGE.start; port <= EXTERNAL_EDITOR_PORT_RANGE.end; port++) {
		try {
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), 500);

			const response = await fetch(`http://127.0.0.1:${port}/status`, {
				method: "GET",
				signal: controller.signal,
			});

			clearTimeout(timeoutId);

			if (response.ok) {
				const data = (await response.json()) as ExternalEditorStatus;
				if (data.active && data.extension === "frappe-script-editor") {
					isExternalEditorActive.value = true;
					externalEditorPort.value = port;
					externalEditorUriScheme.value = data.uriScheme || "vscode";
					editorName.value = data.name;
					return;
				}
			}
		} catch {
			// Port not available or timeout, continue to next
		}
	}
}

async function openInExternalEditor(
	request: OpenScriptRequest,
): Promise<{ success: boolean; error?: string }> {
	if (!isExternalEditorActive.value || !externalEditorPort.value) {
		return { success: false, error: "External editor is not active" };
	}

	try {
		const searchParams = new URLSearchParams();
		searchParams.append("site", window.location.origin);
		searchParams.append("doctype", request.doctype);
		searchParams.append("docname", request.docname);

		if (request.field) searchParams.append("field", request.field);
		if (request.blockId) searchParams.append("blockId", request.blockId);
		if (request.blockField) searchParams.append("blockField", request.blockField);

		const uri = `${
			externalEditorUriScheme.value
		}://frappe.frappe-script-editor/open-script?${searchParams.toString()}`;
		window.location.href = uri;

		return { success: true };
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		return { success: false, error: msg };
	}
}

export function useExternalEditor() {
	onMounted(() => {
		checkExternalEditorStatus();
	});

	return {
		isExternalEditorActive,
		openInExternalEditor,
		editorName,
	};
}

function createEditorContext(
	doctype: string,
	docname: string | undefined | null,
	field?: string,
	blockId?: string,
	blockField?: "blockClientScript" | "blockDataScript",
): OpenScriptRequest | undefined {
	if (!docname) return undefined;
	return {
		site: window.location.origin,
		doctype,
		docname,
		field,
		blockId,
		blockField,
	};
}

export { createEditorContext };
export type { OpenScriptRequest, ExternalEditorStatus };
