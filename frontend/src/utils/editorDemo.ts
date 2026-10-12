import type {
	BlockTemplate,
	BuilderClientScript,
	BuilderComponent,
	BuilderPage,
	BuilderToken,
	UserFont,
} from "@/types/doctypes";

/** A published page and what it renders with, as served to the sandboxed editor demo. */
export type EditorDemoPayload = {
	page: BuilderPage;
	components: Record<string, BuilderComponent>;
	componentVersions: Record<string, BuilderComponent>;
	tokens: BuilderToken[];
	fonts: UserFont[];
	blockTemplates: BlockTemplate[];
	scripts: Pick<BuilderClientScript, "script_type" | "script">[];
};

type Rect = { left: number; top: number; width: number; height: number };
export type EditorDemoMessage = { type: string; scrollY?: number; target?: Rect; dark?: boolean };

const MESSAGE_SOURCE = "builder-editor-demo";

function readPayload(): EditorDemoPayload | null {
	try {
		return JSON.parse(document.getElementById("editor-demo")?.textContent || "");
	} catch {
		return null;
	}
}

function memoryStorage() {
	const items = new Map<string, string>();
	return {
		get length() {
			return items.size;
		},
		key: (index: number) => [...items.keys()][index] ?? null,
		getItem: (key: string) => items.get(key) ?? null,
		setItem: (key: string, value: string) => void items.set(key, String(value)),
		removeItem: (key: string) => void items.delete(key),
		clear: () => items.clear(),
	};
}

export const editorDemo = readPayload();

// the demo shares the site's origin, so it would otherwise read and overwrite the real
// editor's preferences and frappe-ui's IndexedDB resource cache
if (editorDemo) {
	const walls = { localStorage: memoryStorage(), sessionStorage: memoryStorage(), indexedDB: undefined };
	for (const [name, value] of Object.entries(walls)) {
		Object.defineProperty(window, name, { value, configurable: true });
	}
}

export function postToLauncher(message: EditorDemoMessage) {
	window.parent.postMessage({ source: MESSAGE_SOURCE, ...message }, window.location.origin);
}

export function onLauncherMessage(handler: (message: EditorDemoMessage) => void) {
	window.addEventListener("message", (event) => {
		const fromLauncher = event.origin === window.location.origin && event.source === window.parent;
		if (fromLauncher && event.data?.source === MESSAGE_SOURCE) handler(event.data);
	});
}
