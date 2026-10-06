/**
 * The five slot entries of an extension, and the code that runs the slot of this frame.
 *
 * The slot names are fixed. The author does not choose them.
 *
 * Each frame imports the same entry module. So all five registrations run in
 * each frame. The frame then runs only the slot that the handshake named. The
 * frame learns its slot after it reads the module. So one module serves
 * five frames.
 *
 * For the same reason, `main` takes a callback and the other slots take
 * `{ component }`. The entry module always runs. So `main` must wait for its own
 * frame. The module of a slot must not run in a frame for a different slot.
 */

import type { ExtensionSlot } from "../types";

/** The one element that the shell gives a frame for its content. */
const ROOT_ID = "app";

export type VisualSlot = Exclude<ExtensionSlot, "main">;

/** `component` gives the module that has the slot document. */
export type SlotEntry = { component: () => Promise<unknown> };

/**
 * Changes a component into DOM, and returns a cleanup function.
 *
 * The SDK has no framework, so the extension gives this function. It runs in
 * the bundle of the author, in this frame. It does not go through a port.
 */
export type Mounter = (
	component: unknown,
	element: HTMLElement,
	props: Record<string, unknown>,
) => (() => void) | void;

let mainHandler: (() => void) | null = null;
let mounter: Mounter | null = null;
let slot: ExtensionSlot | null = null;
const visualSlots = new Map<VisualSlot, SlotEntry>();

/**
 * Set before the frame imports the entry module. So a registration in that
 * module knows its frame.
 */
export const setActiveSlot = (name: ExtensionSlot) => (slot = name);

export const getActiveSlot = () => slot;

const claim = (slot: ExtensionSlot, taken: boolean) => {
	if (taken) throw new Error(`This extension already registered its "${slot}" slot`);
};

export const registerMain = (handler: () => void) => {
	claim("main", mainHandler !== null);
	mainHandler = handler;
};

export const registerSlot = (slot: VisualSlot, entry: SlotEntry) => {
	claim(slot, visualSlots.has(slot));
	visualSlots.set(slot, entry);
};

/**
 * Sets the adapter that mounts a component. One adapter for each extension.
 *
 * `frappe-builder-extension-sdk/vue` exports one. A second call fails. Two
 * adapters would give two owners for one job.
 */
export const use = (adapter: Mounter) => {
	if (mounter) throw new Error("This extension already registered a mount adapter");
	mounter = adapter;
};

/**
 * The contract between the SDK and the document of an extension.
 *
 * `component()` gives a module. A module does nothing by itself. A framework
 * runtime must change the component into DOM. The extension has a runtime,
 * and the SDK has none. So the extension mounts, and the SDK only calls it.
 * This keeps `extension-sdk.js` small for an extension with no UI.
 *
 * A module has one of two shapes:
 * 1. It exports `mount`. The SDK needs to know no framework.
 * 2. It has a default export of a component. The adapter from `use` mounts it.
 *
 * The cleanup is optional. It runs when the frame closes.
 */
type SlotModule = {
	mount?: (element: HTMLElement, props: Record<string, unknown>) => (() => void) | void;
	default?: unknown;
};

let unmount: (() => void) | void = undefined;

/** Mounts the module. If it cannot, the error tells how to fix it. */
const mount = (module: SlotModule, slot: ExtensionSlot, root: HTMLElement, props: Record<string, unknown>) => {
	if (typeof module.mount === "function") return module.mount(root, props);
	if (mounter && module.default) return mounter(module.default, root, props);
	throw new Error(
		`The module for the "${slot}" slot exports no "mount(element, props)", and this ` +
			`extension registered no mount adapter. Call ` +
			`builder.use(vueAdapter) from "frappe-builder-extension-sdk/vue".`,
	);
};

/**
 * Runs only the slot of this frame.
 *
 * If the extension registered no slot for this frame, it shows a warning, not
 * an error. An extension for a newer Builder can know a slot that this Builder
 * does not open.
 */
export const runSlot = async (props: Record<string, unknown> = {}) => {
	if (slot === "main") return mainHandler?.();

	const entry = slot && visualSlots.get(slot);
	if (!entry) return void console.warn(`This extension registered no "${slot}" slot`);

	const root = document.getElementById(ROOT_ID);
	if (!root) throw new Error(`The extension shell has no #${ROOT_ID} to mount into`);

	const module = (await entry.component()) as SlotModule;
	unmount = mount(module, slot as ExtensionSlot, root, props);

	// the document closes with the frame. This cleanup is for what the document
	// owns: the unmount hooks of a Vue app, a timer, or a subscription
	window.addEventListener("pagehide", () => unmount?.(), { once: true });
};
