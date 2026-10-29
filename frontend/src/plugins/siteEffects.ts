/**
 * A plugin's site code, run on the canvas as on the published page.
 *
 * Site code registers each effect with `builderSite.onBlock(selector, mount)`. A
 * published page mounts it once on each matching block (builder/public/js/plugin_site.js).
 * Here the blocks change while the user edits, so each effect mounts on a matching
 * canvas block, mounts again when the block's data attributes change, and cleans up
 * when the block goes.
 */

type Cleanup = () => void;
type Mount = (element: HTMLElement, context: { editor: boolean }) => void | Cleanup;
type Effect = { plugin: string; selector: string; mount: Mount };
type Mounted = { signature: string; cleanup?: Cleanup };

export type SiteFiles = { plugin: string; script?: string | null; style?: string | null };

declare global {
	interface Window {
		builderSite?: { onBlock: (selector: string, mount: Mount) => void };
	}
}

const effects: Effect[] = [];
const mounted = new Map<HTMLElement, Map<Effect, Mounted>>();
const errors = new Map<string, string[]>();
let observer: MutationObserver | null = null;
let scheduled = 0;

// the canvas draws each breakpoint in a frame of its own, and an effect shows in each
const CANVAS_FRAMES = ".canvas[data-breakpoint]";

/** Site code runs as a classic script, so the script element tells which plugin registers. */
const registeringPlugin = () =>
	(document.currentScript as HTMLScriptElement | null)?.dataset.sitePlugin ?? "";

function start() {
	if (window.builderSite) return;
	window.builderSite = {
		onBlock: (selector, mount) => {
			effects.push({ plugin: registeringPlugin(), selector, mount });
			schedule();
		},
	};
	observer = new MutationObserver(schedule);
	observer.observe(document.body, { subtree: true, childList: true, attributes: true });
}

// many mutations come in one frame while the user edits, so one pass per frame is enough
function schedule() {
	if (!scheduled) scheduled = requestAnimationFrame(reconcile);
}

function reconcile() {
	scheduled = 0;
	const frames = [...document.querySelectorAll<HTMLElement>(CANVAS_FRAMES)];
	const wanted = new Map<HTMLElement, Set<Effect>>();
	for (const effect of effects) {
		for (const element of frames.flatMap((frame) => [...matches(frame, effect.selector)])) {
			wanted.set(element, (wanted.get(element) ?? new Set()).add(effect));
		}
	}
	for (const [element, byEffect] of mounted) {
		for (const effect of byEffect.keys()) if (!wanted.get(element)?.has(effect)) unmount(element, effect);
	}
	for (const [element, byEffect] of wanted) for (const effect of byEffect) ensureMounted(element, effect);
}

function matches(frame: HTMLElement, selector: string): HTMLElement[] {
	try {
		return [...frame.querySelectorAll<HTMLElement>(selector)];
	} catch {
		return [];
	}
}

/** What the effect reads from its block. A change to it mounts the effect again. */
const signatureOf = (element: HTMLElement) => JSON.stringify({ ...element.dataset });

function ensureMounted(element: HTMLElement, effect: Effect) {
	const signature = signatureOf(element);
	const current = mounted.get(element)?.get(effect);
	if (current?.signature === signature) return;
	if (current) unmount(element, effect);
	let cleanup: Cleanup | undefined;
	try {
		cleanup = effect.mount(element, { editor: true }) || undefined;
	} catch (error) {
		recordError(effect.plugin, error);
	}
	const byEffect = mounted.get(element) ?? new Map<Effect, Mounted>();
	byEffect.set(effect, { signature, cleanup });
	mounted.set(element, byEffect);
}

function unmount(element: HTMLElement, effect: Effect) {
	const state = mounted.get(element)?.get(effect);
	try {
		state?.cleanup?.();
	} catch (error) {
		recordError(effect.plugin, error);
	}
	mounted.get(element)?.delete(effect);
	if (!mounted.get(element)?.size) mounted.delete(element);
}

function recordError(plugin: string, error: unknown) {
	const message = error instanceof Error ? `${error.name}: ${error.message}` : String(error);
	errors.set(plugin, [...(errors.get(plugin) ?? []), message]);
	console.error(`[builder] the site code of "${plugin}" failed on the canvas`, error);
}

/** Takes a plugin's effects off the canvas and its site files out of the editor. */
export function unloadSiteFiles(plugin: string) {
	for (const effect of effects.filter((candidate) => candidate.plugin === plugin)) {
		for (const element of [...mounted.keys()]) unmount(element, effect);
		effects.splice(effects.indexOf(effect), 1);
	}
	document.querySelectorAll(`[data-site-plugin="${CSS.escape(plugin)}"]`).forEach((node) => node.remove());
	errors.delete(plugin);
}

/** Loads a release's site files into the editor. A new release of a running plugin replaces the old one. */
export function loadSiteFiles({ plugin, script, style }: SiteFiles): Promise<void> {
	unloadSiteFiles(plugin);
	if (!script && !style) return Promise.resolve();
	start();
	if (style) {
		const link = Object.assign(document.createElement("link"), { rel: "stylesheet", href: style });
		link.dataset.sitePlugin = plugin;
		document.head.append(link);
	}
	if (!script) return Promise.resolve();
	return new Promise((resolve) => {
		const tag = Object.assign(document.createElement("script"), { src: script });
		// an error while the script first runs reaches the window, not the tag
		const onError = (event: ErrorEvent) =>
			event.filename === tag.src && recordError(plugin, event.error ?? event.message);
		const done = () => {
			window.removeEventListener("error", onError);
			resolve();
		};
		tag.dataset.sitePlugin = plugin;
		tag.onload = done;
		tag.onerror = () => {
			recordError(plugin, new Error(`${script} did not load`));
			done();
		};
		window.addEventListener("error", onError);
		document.body.append(tag);
	});
}

export const siteErrors = (plugin: string) => errors.get(plugin) ?? [];
