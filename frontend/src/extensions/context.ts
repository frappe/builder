import { call } from "frappe-ui";
import { reactive } from "vue";

/** What an extension stores for the user who opens the editor. It merges at the top level. */
export type ExtensionState = {
	get: () => Promise<Record<string, unknown>>;
	set: (state: Record<string, unknown>) => Promise<void>;
	unset: (key: string) => Promise<void>;
};

/** The second argument of an extension's `install(app, context)`. */
export type ExtensionContext = {
	name: string;
	label: string;
	version: string;
	state: ExtensionState;
	/** What the Open button in the extension's details pane runs. Without one, the pane shows no button. */
	setOpenHandler: (handler: () => void) => void;
};

export type RunnableExtension = {
	name: string;
	label: string;
	version: string;
	entryUrl: string;
	isDevelopment?: boolean;
};

const STATE_METHOD = "builder.extensions.state";

const serverState = (extension: string): ExtensionState => ({
	get: () => call(`${STATE_METHOD}.get_state`, { extension }),
	set: (state) => call(`${STATE_METHOD}.set_state`, { extension, state }),
	unset: (key) => call(`${STATE_METHOD}.unset_state`, { extension, key }),
});

/** A dev extension stores in this browser. Its installation goes when the developer stops it. */
const browserState = (extension: string): ExtensionState => {
	const key = `builder-extension-state:${extension}`;
	const read = (): Record<string, unknown> => JSON.parse(localStorage.getItem(key) || "{}");
	const write = (state: Record<string, unknown>) => localStorage.setItem(key, JSON.stringify(state));
	return {
		get: async () => read(),
		set: async (state) => write({ ...read(), ...state }),
		unset: async (unsetKey) => {
			const { [unsetKey]: _removed, ...rest } = read();
			write(rest);
		},
	};
};

/** Reactive. The details pane shows its Open button from this. */
export const openHandlers = reactive(new Map<string, () => void>());

export const createExtensionContext = (extension: RunnableExtension): ExtensionContext => ({
	name: extension.name,
	label: extension.label,
	version: extension.version,
	state: extension.isDevelopment ? browserState(extension.name) : serverState(extension.name),
	setOpenHandler: (handler) => openHandlers.set(extension.name, handler),
});
