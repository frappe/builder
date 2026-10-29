import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import { propertySections } from "@/components/BlockPropertySections";
import { leftPanelTabs } from "@/components/LeftPanelTabs";
import { settingsItems } from "@/components/Settings";
import { toolbarItems } from "@/components/ToolbarItems";
import { pluginsDisabled, reloadInstallations, unseenTabs } from "@/data/plugins";
import * as builderAPI from "@/host/builder";
import * as frappeUI from "frappe-ui";
import { call } from "frappe-ui";
import { createVNode, isVNode, nextTick, render, type Component, type VNode } from "vue";
import type { RunnablePlugin } from "./context";
import { getEditorApp, getRunningEntry, loadPlugin, replacePlugin, runningPlugins } from "./loader";
import { loadSiteFiles, siteErrors } from "./siteEffects";

/** What Bob's write_plugin tool sent: the release to load and the token to answer with. */
export type PluginLoadRequest = {
	plugin: string;
	label: string;
	version: string;
	entry_url: string;
	site_script?: string | null;
	site_style?: string | null;
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
// about the width the editor gives a left bar panel
const TEST_WIDTH = 300;
const MIN_CONTRAST = 3;
const NATIVE_CONTROLS = new Set(["input", "select", "textarea", "button"]);
const COLOR_PROPERTIES = ["color", "background-color", "border-color"];
// a control inside one of these was drawn by frappe-ui or Builder, so it already looks like the editor
const hostComponents = new Set<unknown>([...Object.values(frappeUI), ...Object.values(builderAPI)]);

/** Every .vue file the editor ships is compiled with a `__name`; a plugin's h() objects have none. */
const isHostComponent = (type: unknown) =>
	hostComponents.has(type) || (typeof type === "object" && type !== null && "__name" in type);

const lastRegistered = new Map<string, RegisteredItem[]>();

// the chat can hear one realtime event twice, and two loads at once would install the plugin twice
const handledTokens = new Set<string>();

/** Loads Bob's plugin into this editor, checks it, and tells Bob how it went. */
export async function tryPlugin(request: PluginLoadRequest) {
	if (handledTokens.has(request.token)) return;
	handledTokens.add(request.token);
	const report = await loadAndCheck(request);
	await call("builder.plugins.bob.report_load", { token: request.token, report }).catch((error: Error) =>
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
	const componentProblems = await checkComponents(components, request.entry_url);
	const siteProblems = await checkSiteFiles(request);
	return {
		registered,
		problems: [...iconProblems(added.map(({ item }) => item)), ...componentProblems, ...siteProblems],
	};
}

/** Its site code runs on the canvas as on the published page, so its errors show up here too. */
async function checkSiteFiles(request: PluginLoadRequest): Promise<string[]> {
	await loadSiteFiles({ plugin: request.plugin, script: request.site_script, style: request.site_style });
	await new Promise((resolve) => setTimeout(resolve, RENDER_SETTLE_MS));
	return siteErrors(request.plugin).map((error) => `site.js threw on the canvas: ${error}`);
}

/** A string draws only as a lucide class that the editor's own build uses, so a plugin passes lucideIcon(). */
function iconProblems(items: AnyItem[]): string[] {
	return items
		.filter((item) => typeof item.icon === "string")
		.map((item) => `${item.name}: the icon "${item.icon}" draws nothing. Pass lucideIcon("lucide-<name>").`);
}

/**
 * Mounts each new component once, out of sight and in dark mode, so what the user
 * would hit on opening it reaches Bob now: an error, a control frappe-ui did not
 * draw, a color that does not follow the theme.
 */
async function checkComponents(items: RenderableItem[], entryUrl: string): Promise<string[]> {
	const container = testContainer();
	const problems: string[] = [];
	const errors = await collectErrors(entryUrl, async () => {
		for (const item of items) problems.push(...(await checkComponent(item, container)));
	});
	container.remove();
	return [
		...errors.map((error) => `A component threw when the editor test-rendered it:\n${error}`),
		...problems,
	];
}

async function checkComponent(item: RenderableItem, container: HTMLElement): Promise<string[]> {
	const vnode = createVNode(item.component, item.props?.() ?? {});
	vnode.appContext = getEditorApp()._context;
	render(vnode, container);
	await nextTick();
	await new Promise((resolve) => setTimeout(resolve, RENDER_SETTLE_MS));
	const ownElements = authoredElements(vnode);
	const problems = [
		...nativeControls(ownElements, item.name),
		...fixedColors(ownElements, item.name),
		...unreadableText(container, item.name),
	];
	render(null, container);
	return problems;
}

/** The theme tokens follow `data-theme` on any element, so this one shows its content in dark mode. */
function testContainer(): HTMLElement {
	const container = document.createElement("div");
	container.dataset.theme = "dark";
	container.className = "bg-surface-base";
	container.setAttribute("aria-hidden", "true");
	Object.assign(container.style, { position: "fixed", left: "-10000px", top: "0", width: `${TEST_WIDTH}px` });
	document.body.append(container);
	return container;
}

async function collectErrors(entryUrl: string, run: () => Promise<void>): Promise<string[]> {
	const app = getEditorApp();
	const errors: string[] = [];
	const collect = (error: unknown) => errors.push(describeError(error, entryUrl));
	const onError = (event: ErrorEvent) => collect(event.error ?? event.message);
	const onRejection = (event: PromiseRejectionEvent) => collect(event.reason);

	const handler = app.config.errorHandler;
	app.config.errorHandler = collect;
	window.addEventListener("error", onError);
	window.addEventListener("unhandledrejection", onRejection);
	try {
		await run();
	} catch (error) {
		collect(error);
	} finally {
		app.config.errorHandler = handler;
		window.removeEventListener("error", onError);
		window.removeEventListener("unhandledrejection", onRejection);
	}
	return [...new Set(errors)];
}

/**
 * The elements the plugin's own render functions made, not the ones inside a frappe-ui
 * or Builder component. Found through the vnode tree, which production builds keep.
 */
function authoredElements(root: VNode): HTMLElement[] {
	const elements: HTMLElement[] = [];
	const walk = (vnode: VNode, insideHost: boolean) => {
		if (vnode.component) return walk(vnode.component.subTree, insideHost || isHostComponent(vnode.type));
		if (!insideHost && vnode.el instanceof HTMLElement) elements.push(vnode.el);
		if (Array.isArray(vnode.children)) {
			vnode.children.forEach((child) => isVNode(child) && walk(child, insideHost));
		}
	};
	walk(root, false);
	return elements;
}

function nativeControls(elements: HTMLElement[], name: string): string[] {
	const tags = new Set(
		elements.map((element) => element.tagName.toLowerCase()).filter((tag) => NATIVE_CONTROLS.has(tag)),
	);
	if (!tags.size) return [];
	const listed = [...tags].map((tag) => `<${tag}>`).join(", ");
	return [
		`${name}: draws its own ${listed}. Use frappe-ui's Button and FormControl so it looks like the rest of the editor.`,
	];
}

/** A color written into a style attribute stays the same when the editor switches theme. */
function fixedColors(elements: HTMLElement[], name: string): string[] {
	const fixed = elements.flatMap((element) =>
		COLOR_PROPERTIES.map((property) => element.style.getPropertyValue(property)).filter(isFixedColor),
	);
	if (!fixed.length) return [];
	return [
		`${name}: ${fixed.length} inline colors, such as ${fixed[0]}, stay the same in dark mode. Use text-ink-gray-*, bg-surface-* and border-outline-* classes instead.`,
	];
}

const isFixedColor = (value: string) =>
	Boolean(value) && !/var\(|inherit|currentcolor|transparent|initial|unset/i.test(value);

function unreadableText(container: HTMLElement, name: string): string[] {
	if (!pixel) return [];
	const samples: string[] = [];
	for (const element of container.querySelectorAll<HTMLElement>("*")) {
		const text = ownText(element);
		if (!text || !element.getClientRects().length) continue;
		const ratio = contrast(toRGBA(getComputedStyle(element).color), backgroundOf(element, container));
		if (ratio < MIN_CONTRAST) samples.push(`"${text.slice(0, 40)}" (contrast ${ratio.toFixed(1)})`);
	}
	if (!samples.length) return [];
	return [
		`${name}: text that cannot be read in dark mode: ${samples.slice(0, 3).join(", ")}. Give every text element a text-ink-gray-* class; inherited text is dark in dark mode.`,
	];
}

const ownText = (element: HTMLElement) =>
	[...element.childNodes]
		.filter((node) => node.nodeType === Node.TEXT_NODE)
		.map((node) => node.textContent)
		.join("")
		.trim();

type RGBA = [number, number, number, number];

/** The first ancestor background that hides what is behind it, up to the panel itself. */
function backgroundOf(element: HTMLElement, container: HTMLElement): RGBA {
	for (let node: HTMLElement | null = element; node && node !== container; node = node.parentElement) {
		const color = toRGBA(getComputedStyle(node).backgroundColor);
		if (color[3] > 0.5) return color;
	}
	return toRGBA(getComputedStyle(container).backgroundColor);
}

const pixel = document.createElement("canvas").getContext("2d", { willReadFrequently: true });

/** Computed colors come in any syntax the browser speaks (rgb, lab, color()). A canvas reads them all. */
function toRGBA(color: string): RGBA {
	if (!pixel) return [0, 0, 0, 1];
	pixel.clearRect(0, 0, 1, 1);
	pixel.fillStyle = color;
	pixel.fillRect(0, 0, 1, 1);
	const [red, green, blue, alpha] = pixel.getImageData(0, 0, 1, 1).data;
	return [red, green, blue, alpha / 255];
}

/** WCAG contrast, with a translucent text color laid over its background first. */
function contrast(text: RGBA, background: RGBA): number {
	const alpha = text[3];
	const blended = text.slice(0, 3).map((channel, index) => channel * alpha + background[index] * (1 - alpha));
	const [lighter, darker] = [luminance(blended), luminance(background.slice(0, 3))].sort((a, b) => b - a);
	return (lighter + 0.05) / (darker + 0.05);
}

function luminance(rgb: number[]): number {
	const [red, green, blue] = rgb.map((channel) => {
		const value = channel / 255;
		return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
	});
	return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
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
