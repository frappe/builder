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
	scripts: Pick<BuilderClientScript, "name" | "script_type" | "script">[];
};

export type EditorDemoMessage =
	| { type: "booted" }
	| { type: "ready" }
	| { type: "exit"; scrollY: number }
	| {
			type: "prepare";
			scrollY: number;
			target?: { left: number; top: number; width: number; height: number } | null;
	  }
	| { type: "play" }
	| { type: "close" };

const MESSAGE_SOURCE = "builder-editor-demo";

function readPayload(): EditorDemoPayload | null {
	try {
		return JSON.parse(document.getElementById("editor-demo")?.textContent || "");
	} catch {
		return null;
	}
}

class MemoryStorage implements Storage {
	[key: string]: any;
	private items = new Map<string, string>();
	get length() {
		return this.items.size;
	}
	clear() {
		this.items.clear();
	}
	getItem(key: string) {
		return this.items.get(key) ?? null;
	}
	key(index: number) {
		return Array.from(this.items.keys())[index] ?? null;
	}
	removeItem(key: string) {
		this.items.delete(key);
	}
	setItem(key: string, value: string) {
		this.items.set(key, String(value));
	}
}

// the demo shares the site's origin, so it would otherwise read and overwrite the
// real editor's preferences and frappe-ui's IndexedDB resource cache
function isolateStorage() {
	const replacements = {
		localStorage: new MemoryStorage(),
		sessionStorage: new MemoryStorage(),
		indexedDB: undefined,
	};
	for (const [name, value] of Object.entries(replacements)) {
		Object.defineProperty(window, name, { value, configurable: true });
	}
}

export const editorDemo = readPayload();

if (editorDemo) {
	isolateStorage();
}

export function postToLauncher(message: EditorDemoMessage) {
	if (window.parent !== window) {
		window.parent.postMessage({ source: MESSAGE_SOURCE, ...message }, window.location.origin);
	}
}

export function onLauncherMessage(handler: (message: EditorDemoMessage) => void) {
	const listener = (event: MessageEvent) => {
		const fromLauncher = event.origin === window.location.origin && event.source === window.parent;
		if (fromLauncher && event.data?.source === MESSAGE_SOURCE) {
			handler(event.data as EditorDemoMessage);
		}
	};
	window.addEventListener("message", listener);
	return () => window.removeEventListener("message", listener);
}
