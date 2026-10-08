/**
 * Code that runs the slots of extensions.
 * Each frame imports the entry module and runs only its own slot.
 */

import type { ExtensionSlot } from "../shared/types";

/** The element that the shell gives a frame for its content. */
const ROOT_ID = "app";

export type VisualSlot = Exclude<ExtensionSlot, "main">;

/** `component` returns the module of the slot. */
export type SlotEntry = { component: () => Promise<unknown> };

/** Mounts a component and returns a cleanup function. The extension gives this function. */
export type Mounter = (
	component: unknown,
	element: HTMLElement,
	props: Record<string, unknown>,
) => (() => void) | void;

let mainHandler: (() => void) | null = null;
let mounter: Mounter | null = null;
let slot: ExtensionSlot | null = null;
const visualSlots = new Map<VisualSlot, SlotEntry>();

/** Set before the frame imports the entry. So a registration knows its frame. */
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

/** Sets the adapter that mounts a component. A second call fails. */
export const use = (adapter: Mounter) => {
	if (mounter) throw new Error("This extension already registered a mount adapter");
	mounter = adapter;
};

/**
 * A slot module exports `mount`, or has a default export of a component for the adapter.
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
 * Runs only the slot of this frame. If there is no slot, it shows a warning.
 * An extension for a newer Builder can have a slot that this Builder does not open.
 */
export const runSlot = async (props: Record<string, unknown> = {}) => {
	if (slot === "main") return mainHandler?.();

	const entry = slot && visualSlots.get(slot);
	if (!entry) return void console.warn(`This extension registered no "${slot}" slot`);

	const root = document.getElementById(ROOT_ID);
	if (!root) throw new Error(`The extension shell has no #${ROOT_ID} to mount into`);

	const module = (await entry.component()) as SlotModule;
	unmount = mount(module, slot as ExtensionSlot, root, props);

	// The cleanup is for the Vue app, timers and subscriptions of the slot.
	window.addEventListener("pagehide", () => unmount?.(), { once: true });
};
