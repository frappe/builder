import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import { propertySections } from "@/components/BlockPropertySections";
import { leftPanelTabs } from "@/components/LeftPanelTabs";
import { settingsItems } from "@/components/Settings";
import { toolbarItems } from "@/components/ToolbarItems";
import { pluginsDisabled, reloadInstallations, unseenTabs } from "@/data/plugins";
import { call } from "frappe-ui";
import { createVNode, nextTick, render, type Component } from "vue";
import type { RunnablePlugin } from "./context";
import { getEditorApp, getRunningEntry, loadPlugin, replacePlugin, runningPlugins } from "./loader";

/** What Bob's write_plugin tool sent: the draft to load and the token to answer with. */
export type PluginLoadRequest = {
	plugin: string;
	label: string;
	version: string;
	entry_url: string;
	token: string;
};

type RegisteredItem = { surface: string; name: string; label: string };

type LoadReport = {
	disabled?: boolean;
	unchanged?: boolean;
	error?: string;
	registered?: RegisteredItem[];
	/** What Bob must fix although the plugin loaded: an icon that draws nothing, a component that throws. */
	problems?: string[];
};

type AnyItem = {
	name: string;
	label?: string;
	icon?: unknown;
	component?: Component;
	props?: () => Record<string, unknown>;
};

type RenderableItem = AnyItem & { component: Component };

// keyed by the names that write_plugin turns into words for Bob
const registries: Record<string, { all: { value: AnyItem[] } }> = {
	leftPanelTabs,
	toolbarItems,
	blockContextMenuOptions,
	propertySections,
	settingsItems,
};

// a panel that fetches in onMounted gets this long to fail before the test render ends
const RENDER_SETTLE_MS = 400;

const lastRegistered = new Map<string, RegisteredItem[]>();

// the chat can hear one realtime event twice, and two loads at once would install the plugin twice
const handledTokens = new Set<string>();

/** Loads Bob's draft into this editor, checks it, and tells Bob how it went. */
export async function tryPlugin(request: PluginLoadRequest) {
	if (handledTokens.has(request.token)) return;
	handledTokens.add(request.token);
	const report = await loadAndCheck(request);
	await call("builder.plugins.drafts.report_load", { token: request.token, report }).catch((error: Error) =>
		console.error("[builder] could not report the plugin load", error),
	);
	await reloadInstallations();
	for (const item of report.registered ?? []) {
		if (item.surface === "leftPanelTabs") unseenTabs.add(item.name);
	}
}

async function loadAndCheck(request: PluginLoadRequest): Promise<LoadReport> {
	if (pluginsDisabled.value) return { disabled: true };
	if (getRunningEntry(request.plugin) === request.entry_url) {
		return { unchanged: true, registered: lastRegistered.get(request.plugin) ?? [] };
	}

	const plugin: RunnablePlugin = {
		name: request.plugin,
		label: request.label,
		version: request.version,
		entryUrl: request.entry_url,
	};
	const before = new Set(Object.values(registries).flatMap((registry) => registry.all.value));
	try {
		await (runningPlugins.has(plugin.name) ? replacePlugin(plugin) : loadPlugin(plugin));
	} catch (error) {
		return { error: describeError(error, request.entry_url) };
	}

	const added = Object.entries(registries).flatMap(([surface, registry]) =>
		registry.all.value.filter((item) => !before.has(item)).map((item) => ({ surface, item })),
	);
	const registered = added.map(({ surface, item }) => ({
		surface,
		name: item.name,
		label: item.label ?? item.name,
	}));
	lastRegistered.set(plugin.name, registered);
	const components = added
		.map(({ item }) => item)
		.filter((item): item is RenderableItem => Boolean(item.component));
	const renderProblems = (await renderErrors(components, request.entry_url)).map(
		(error) => `A component threw when the editor test-rendered it:\n${error}`,
	);
	return { registered, problems: [...iconProblems(added.map(({ item }) => item)), ...renderProblems] };
}

/** A string draws only as a lucide class that the editor's own build uses, so a plugin passes lucideIcon(). */
function iconProblems(items: AnyItem[]): string[] {
	return items
		.filter((item) => typeof item.icon === "string")
		.map((item) => `${item.name}: the icon "${item.icon}" draws nothing. Pass lucideIcon("lucide-<name>").`);
}

/**
 * Mounts each new component once, out of sight, so an error in a panel reaches
 * Bob now and not when the user first opens it.
 */
async function renderErrors(items: RenderableItem[], entryUrl: string): Promise<string[]> {
	const app = getEditorApp();
	const errors: string[] = [];
	const collect = (error: unknown) => errors.push(describeError(error, entryUrl));
	const onError = (event: ErrorEvent) => collect(event.error ?? event.message);
	const onRejection = (event: PromiseRejectionEvent) => collect(event.reason);

	const handler = app.config.errorHandler;
	app.config.errorHandler = collect;
	window.addEventListener("error", onError);
	window.addEventListener("unhandledrejection", onRejection);
	const container = document.createElement("div");
	try {
		for (const item of items) {
			const vnode = createVNode(item.component, item.props?.() ?? {});
			vnode.appContext = app._context;
			render(vnode, container);
			await nextTick();
			await new Promise((resolve) => setTimeout(resolve, RENDER_SETTLE_MS));
			render(null, container);
		}
	} catch (error) {
		collect(error);
	} finally {
		app.config.errorHandler = handler;
		window.removeEventListener("error", onError);
		window.removeEventListener("unhandledrejection", onRejection);
	}
	return [...new Set(errors)];
}

/** The message and the first frames, with the long release URL shortened to main.js. */
function describeError(error: unknown, entryUrl: string): string {
	const text =
		error instanceof Error
			? `${error.name}: ${error.message}\n${error.stack ?? ""}`
			: String(error ?? "Unknown error");
	const entry = new URL(entryUrl, window.location.origin).href;
	const lines = text.split(entry).join("main.js").split("\n");
	return [...new Set(lines)].slice(0, 6).join("\n");
}
