/** The registrations of the left panel, the toolbar, the context menu, properties and settings. */

import { registerSlot } from "../slots";
import { resolveAction, type ActionRef } from "./actions";
import { call, callFromEntryOnly } from "./call";

/** The host keeps the action of a control under the section name too. So two sections can use the same control name. */
const resolveControls = (section: string, controls: Control[]) =>
	controls.map((control) => resolveAction(control, `${section}.`));

export type ShowWhen = Record<string, unknown>;

/** Gives the module that has the document of the slot. */
export type SlotLoader = () => Promise<unknown>;

export type LeftPanelRegistration = {
	name: string;
	label: string;
	icon: string;
	/** What the frame of the tab shows. It is declared here, because the tab shows it. */
	component?: SlotLoader;
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
};

export type ToolbarRegistration = {
	name: string;
	region: "left" | "center" | "right";
	icon: string;
	label?: string;
	tooltip?: string;
	/** A function, or the name of an action that this extension registered. */
	action?: ActionRef;
	badge?: string | number | null;
	/** In the right region, these place a button among the extension buttons only. Builder's own buttons stay at the right end. */
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
	enableWhen?: ShowWhen;
};

export type ContextMenuRegistration = {
	name: string;
	label: string;
	/** A function, or the name of an action that this extension registered. */
	action: ActionRef;
	/** The menu of the row. It is set at registration. The default is "both". */
	menu?: "canvas" | "layers" | "both";
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
	enableWhen?: ShowWhen;
};

export type SettingsRegistration = {
	name: string;
	label: string;
	title: string;
	icon: string;
	/** What the settings frame shows. It is declared here, because this item shows it. */
	component?: SlotLoader;
	before?: string;
	after?: string;
};

/** The Builder control that the host shows. A section holds values, not buttons. */
export type ControlName = "text" | "number" | "select" | "toggle" | "color" | "range";

/** One control in a property section (Tier B). The host shows it. */
export type Control = {
	name: string;
	control: ControlName;
	label?: string;
	placeholder?: string;
	/** The host writes the block itself. Needs the `page.edit` permission. */
	bind?: { attribute?: string; style?: string };
	/** The value of the extension, when no block property holds it. */
	value?: unknown;
	/** The action to run after a bound write. If the control is not bound, it runs on each change. */
	action?: ActionRef;
	/** For "select" and "toggle". A toggle option can have an icon. */
	options?: Array<{ label: string; value: string; icon?: string }>;
	min?: number;
	max?: number;
	step?: number;
	/** For each control. So one control can hide while the rest of the section stays. */
	showWhen?: ShowWhen;
};

export type PropertiesRegistration = {
	name: string;
	/** The section header. The default is `name`. */
	label?: string;
	controls: Control[];
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
};

export type ItemPatch = {
	visible?: boolean;
	enabled?: boolean;
	label?: string;
	icon?: string;
	tooltip?: string;
	badge?: string | number | null;
};

export const leftPanel = {
	register: ({ component, ...registration }: LeftPanelRegistration) => {
		// each frame records it. The panel frame uses it. No frame sends it
		if (component) registerSlot("panel", { component });
		return callFromEntryOnly("leftPanel.register", registration);
	},
	unregister: (name: string) => call("leftPanel.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("leftPanel.update", { name, patch }),
};

export const toolbar = {
	register: (registration: ToolbarRegistration) =>
		callFromEntryOnly("toolbar.register", resolveAction(registration)),
	unregister: (name: string) => call("toolbar.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("toolbar.update", { name, patch }),
};

export const contextMenu = {
	register: (registration: ContextMenuRegistration) =>
		callFromEntryOnly("contextMenu.register", resolveAction(registration)),
	unregister: (name: string) => call("contextMenu.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("contextMenu.update", { name, patch }),
};

export const properties = {
	registerSection: (registration: PropertiesRegistration) =>
		callFromEntryOnly("properties.registerSection", {
			...registration,
			controls: resolveControls(registration.name, registration.controls),
		}),
	unregisterSection: (name: string) => call("properties.unregisterSection", { name }),
	/** Replaces the full list. Use it when the control list depends on the state of the extension. */
	setControls: (name: string, controls: Control[]) =>
		call("properties.setControls", { name, controls: resolveControls(name, controls) }),
	update: (name: string, patch: ItemPatch) => call("properties.update", { name, patch }),
};

export const settings = {
	registerItem: ({ component, ...registration }: SettingsRegistration) => {
		if (component) registerSlot("settings", { component });
		return callFromEntryOnly("settings.registerItem", registration);
	},
	unregisterItem: (name: string) => call("settings.unregisterItem", { name }),
	update: (name: string, patch: ItemPatch) => call("settings.update", { name, patch }),
};
