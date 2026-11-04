import { call } from "frappe-ui";
import { reactive } from "vue";

/** What a plugin stores for the user who opens the editor. It merges at the top level. */
export type PluginState = {
	get: () => Promise<Record<string, unknown>>;
	set: (state: Record<string, unknown>) => Promise<void>;
	unset: (key: string) => Promise<void>;
};

/** The second argument of a plugin's `install(app, context)`. */
export type PluginContext = {
	name: string;
	label: string;
	version: string;
	state: PluginState;
	/** What the Open button in the plugin's details pane runs. Without one, the pane shows no button. */
	setOpenHandler: (handler: () => void) => void;
};

export type RunnablePlugin = {
	name: string;
	label: string;
	version: string;
	entryUrl: string;
	isDevelopment?: boolean;
};

const STATE_METHOD = "builder.plugins.state";

const serverState = (plugin: string): PluginState => ({
	get: () => call(`${STATE_METHOD}.get_state`, { plugin }),
	set: (state) => call(`${STATE_METHOD}.set_state`, { plugin, state }),
	unset: (key) => call(`${STATE_METHOD}.unset_state`, { plugin, key }),
});

/** A dev plugin stores in this browser. Its installation goes when the developer stops it. */
const browserState = (plugin: string): PluginState => {
	const key = `builder-plugin-state:${plugin}`;
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

export const createPluginContext = (plugin: RunnablePlugin): PluginContext => ({
	name: plugin.name,
	label: plugin.label,
	version: plugin.version,
	state: plugin.isDevelopment ? browserState(plugin.name) : serverState(plugin.name),
	setOpenHandler: (handler) => openHandlers.set(plugin.name, handler),
});
