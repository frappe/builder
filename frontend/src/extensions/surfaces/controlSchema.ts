/**
 * Changes one control, sent as data, into the `BlockProperty` that the right
 * panel shows (Tier B). An extension sends no components and no functions. So
 * only this file knows which Builder control matches which name.
 *
 * Two components make one control. The wrapper decides where the value is
 * stored. The inner widget is what the user uses. The Builder sections use
 * the same design (see `StyleSection.ts`).
 *
 * | `bind`        | wrapper                   | who writes the block   |
 * | attribute     | AttributePropertyControl  | the wrapper, by default |
 * | style         | StylePropertyControl      | the wrapper, by default |
 * | none          | BasePropertyControl       | nobody: the extension acts |
 *
 * A `bind` control with no `action` becomes only a `propertyKey`, because both
 * bound wrappers already do the write. Only the two shapes that need more than
 * a write get a `setModelValue` here.
 */

import type { BlockProperty } from "@/components/BlockPropertySections";
import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import RangeInput from "@/components/Controls/RangeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { editorContext } from "../context/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../context/showWhen";
import { canWrite } from "../bridge/permissions";
import { fields, oneOf, optionalText, refuse, text } from "../bridge/params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { invokeAction } from "./actionMethods";

/**
 * The widgets that the Builder sections use most. It does not include the
 * widgets that an extension cannot give as data. `Autocomplete` needs a
 * `getOptions` function, and `FontInput` loads web fonts.
 *
 * `text` names no widget, because `Input` is the default of the wrapper. No
 * wrapper declares `type` and `options`. So Vue passes them to the widget
 * through `useAttrs` (see `BasePropertyControl.vue`).
 */
const WIDGETS = {
	text: {},
	number: { type: "number" },
	select: { type: "select" },
	toggle: { component: OptionToggle },
	color: { component: ColorInput },
	range: { component: RangeInput },
} as const;

const CONTROL_NAMES = Object.keys(WIDGETS) as (keyof typeof WIDGETS)[];

type Bind = { attribute?: string; style?: string };

export type Control = {
	name: string;
	control: keyof typeof WIDGETS;
	label?: string;
	placeholder?: string;
	bind?: Bind;
	/** The value of the extension, when no block property holds it. */
	value?: unknown;
	action?: string;
	options?: unknown;
	min?: number;
	max?: number;
	step?: number;
	showWhen?: ShowWhenRule;
};

const number = (value: unknown) => (typeof value === "number" ? value : undefined);

/** Neither key is required. But a bind with neither key would write to nothing. */
const readBind = (value: unknown, name: string): Bind | undefined => {
	if (value === undefined) return undefined;
	const sent = fields(value);
	const bind = {
		attribute: optionalText(sent.attribute, "bind.attribute"),
		style: optionalText(sent.style, "bind.style"),
	};
	if (!bind.attribute && !bind.style) {
		throw refuse(`"${name}" binds to neither an attribute nor a style.`, "invalid_params");
	}
	return bind;
};

const readControl = (params: unknown): Control => {
	const sent = fields(params);
	assertRule(sent.showWhen as ShowWhenRule | undefined);

	const name = text(sent.name, "name");
	const control = {
		name,
		control: oneOf(sent.control, CONTROL_NAMES, "control"),
		label: optionalText(sent.label, "label"),
		placeholder: optionalText(sent.placeholder, "placeholder"),
		bind: readBind(sent.bind, name),
		value: sent.value,
		action: optionalText(sent.action, "action"),
		options: sent.options,
		min: number(sent.min),
		max: number(sent.max),
		step: number(sent.step),
		showWhen: sent.showWhen as ShowWhenRule | undefined,
	};

	// a control that does not write and has no action would show and do nothing
	if (!control.bind && !control.action) {
		throw refuse(`"${name}" has neither "bind" nor "action", so it does nothing.`, "invalid_params");
	}
	return control;
};

/**
 * The permission gate for all the controls at one time.
 *
 * The check occurs at registration, when there is no call to gate.
 * `setControls` replaces the full list. So it is a second way to change the
 * same state, and it gets the same check. That is why this check is in the
 * reader, not in the method.
 */
export const readControls = (params: unknown, extension: InstalledExtension): Control[] => {
	if (!Array.isArray(params)) throw refuse(`"controls" must be a list.`, "invalid_params");

	const controls = params.map(readControl);
	if (controls.some((control) => control.bind) && !canWrite(extension)) {
		throw refuse(
			`"${extension.name}" was not granted page.edit, which a bound control needs.`,
			"permission_required",
		);
	}
	return controls;
};

const writeTo = (bind: Bind) => (value: string | number | boolean) =>
	bind.attribute
		? blockController.setAttribute(bind.attribute, String(value))
		: blockController.setStyle(bind.style as string, value);

/** The plain context that an action gets. A menu row sends the same shape. */
const notify = (control: Control, extension: InstalledExtension) => (value: unknown) =>
	void invokeAction(extension, control.action as string, {
		name: control.name,
		blockId: editorContext.value.selection.blockId,
		value,
	});

/**
 * A bound control with no action returns nothing. The default of the wrapper
 * reads and writes the block.
 */
const valueProps = (control: Control, extension: InstalledExtension) => {
	const tell = control.action ? notify(control, extension) : undefined;
	if (!control.bind) return { getModelValue: () => control.value, setModelValue: tell };
	if (!tell) return {};

	const write = writeTo(control.bind);
	return {
		setModelValue: (value: string | number | boolean) => {
			write(value);
			tell(value);
		},
	};
};

const wrapperFor = (control: Control) => {
	if (control.bind?.attribute) return AttributePropertyControl;
	if (control.bind?.style) return StylePropertyControl;
	return BasePropertyControl;
};

export const toBlockProperty = (
	control: Control,
	extension: InstalledExtension,
	sectionLabel: string,
): BlockProperty => ({
	component: wrapperFor(control),
	getProps: () => ({
		label: control.label,
		// a control that is not bound has no block property. So its name identifies it
		propertyKey: control.bind?.attribute ?? control.bind?.style ?? control.name,
		placeholder: control.placeholder,
		options: control.options,
		min: control.min,
		max: control.max,
		step: control.step,
		...WIDGETS[control.control],
		...valueProps(control, extension),
	}),
	// the search filter of the panel reads this, and the type needs it
	searchKeyWords: [sectionLabel, control.label, control.name].filter(Boolean).join(", "),
	condition: control.showWhen ? () => matches(control.showWhen, editorContext.value) : undefined,
});
