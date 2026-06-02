import { ref, onMounted } from "vue";

const EXTERNAL_EDITOR_PORT_RANGE = { start: 59000, end: 59021 };

type PermissionState = "granted" | "denied" | "prompt" | "unsupported";

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
const lnaPermissionStatus = ref<PermissionState>("prompt");
const isRequestingAccess = ref(false);

async function checkLocalNetworkAccess(): Promise<void> {
	try {
		const result = await navigator.permissions.query({
			name: "local-network-access" as PermissionName,
		});
		lnaPermissionStatus.value = result.state as PermissionState;
		result.addEventListener("change", () => {
			lnaPermissionStatus.value = result.state as PermissionState;
		});
	} catch {
		lnaPermissionStatus.value = "unsupported";
	}
}

async function scanPorts(
	options: {
		timeout?: number;
		validateResponse?: (data: ExternalEditorStatus) => boolean;
	} = {},
): Promise<{ port: number; data?: ExternalEditorStatus } | null> {
	const { timeout = 500, validateResponse } = options;

	for (let port = EXTERNAL_EDITOR_PORT_RANGE.start; port <= EXTERNAL_EDITOR_PORT_RANGE.end; port++) {
		try {
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), timeout);

			const response = await fetch(`http://127.0.0.1:${port}/status`, {
				method: "GET",
				signal: controller.signal,
			});

			clearTimeout(timeoutId);

			if (response.ok) {
				const data = (await response.json()) as ExternalEditorStatus;
				if (!validateResponse || validateResponse(data)) {
					return { port, data };
				}
			}
		} catch {}
	}
	return null;
}

async function requestLocalNetworkAccess(): Promise<void> {
	isRequestingAccess.value = true;
	try {
		await scanPorts({ timeout: 300 });
	} catch {}
	await checkLocalNetworkAccess();
	isRequestingAccess.value = false;
}

async function checkExternalEditorStatus(): Promise<void> {
	isExternalEditorActive.value = false;
	externalEditorPort.value = null;

	if (lnaPermissionStatus.value === "denied") return;

	const result = await scanPorts({
		validateResponse: (data) => data.active && data.extension === "frappe-script-editor",
	});

	if (result) {
		isExternalEditorActive.value = true;
		externalEditorPort.value = result.port;
		externalEditorUriScheme.value = result.data?.uriScheme || "vscode";
		editorName.value = result.data?.name || "VS Code";
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
		}://PratikBadhe.frappe-script-editor/open-script?${searchParams.toString()}`;
		window.location.href = uri;

		return { success: true };
	} catch (err) {
		const msg = err instanceof Error ? err.message : String(err);
		return { success: false, error: msg };
	}
}

export function useExternalEditor() {
	onMounted(async () => {
		await checkLocalNetworkAccess();
		if (!isExternalEditorActive.value && (lnaPermissionStatus.value === "granted" || import.meta.env.DEV)) {
			await checkExternalEditorStatus();
		}
	});

	return {
		isExternalEditorActive,
		openInExternalEditor,
		editorName,
		lnaPermissionStatus,
		isRequestingAccess,
		requestLocalNetworkAccess,
		checkLocalNetworkAccess,
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
