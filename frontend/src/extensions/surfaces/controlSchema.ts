/**
 * One control, as data, turned into the `BlockProperty` the right panel renders
 * (Tier B). Nothing an extension sends is a component or a function, so this
 * file is the only place that knows which Builder control answers which name.
 *
 * Two components make one control. The wrapper decides where the value lives,
 * and the inner widget decides what the user touches, exactly as Builder's own
 * sections are written (`StyleSection.ts:38`).
 *
 * | `bind`        | wrapper                   | who writes the block   |
 * | attribute     | AttributePropertyControl  | the wrapper, by default |
 * | style         | StylePropertyControl      | the wrapper, by default |
 * | none          | BasePropertyControl       | nobody: the extension acts |
 *
 * A `bind` control with no `action` synthesizes to a `propertyKey` and nothing
 * else, because both bound wrappers already carry the write. Only the two
 * shapes that need more than a write get a `setModelValue` from here.
 */

import type { BlockProperty } from "@/components/BlockPropertySections";
import AttributePropertyControl from "@/components/Controls/AttributePropertyControl.vue";
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import RangeInput from "@/components/Controls/RangeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { editorContext } from "../editor/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../editor/showWhen";
import { canWrite } from "../host/capabilities";
import { fields, oneOf, optionalText, refuse, text } from "../params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { invokeAction } from "./actionMethods";

/**
 * The widgets Builder's own sections use most, less the ones an extension
 * cannot describe as data: `Autocomplete` wants a `getOptions` function, and
 * `FontInput` loads webfonts as a side effect.
 *
 * `text` names no widget, because `Input` is the wrapper's default. `type` and
 * `options` are declared by no wrapper, so Vue passes them through `useAttrs`
 * to the widget (`BasePropertyControl.vue:130`).
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
	/** The extension's own value, when no block property holds it. */
	value?: unknown;
	action?: string;
	options?: unknown;
	min?: number;
	max?: number;
	step?: number;
	showWhen?: ShowWhenRule;
};

const number = (value: unknown) => (typeof value === "number" ? value : undefined);

/** Neither key is required, but a bind that names neither would write nowhere. */
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

	// a control that neither writes nor reports would render and do nothing
	if (!control.bind && !control.action) {
		throw refuse(`"${name}" has neither "bind" nor "action", so it does nothing.`, "invalid_params");
	}
	return control;
};

/**
 * The gate B3 describes, over every control at once.
 *
 * B3 puts it at registration, where there is no call to gate. `setControls`
 * replaces the whole list, so it is a second door into the same state and gets
 * the same check. That is why this lives with the reader, not with the method.
 */
export const readControls = (params: unknown, extension: InstalledExtension): Control[] => {
	if (!Array.isArray(params)) throw refuse(`"controls" must be a list.`, "invalid_params");

	const controls = params.map(readControl);
	if (controls.some((control) => control.bind) && !canWrite(extension)) {
		throw refuse(
			`"${extension.name}" was not granted block.update, which a bound control needs.`,
			"capability_required",
		);
	}
	return controls;
};

const writeTo = (bind: Bind) => (value: string | number | boolean) =>
	bind.attribute
		? blockController.setAttribute(bind.attribute, String(value))
		: blockController.setStyle(bind.style as string, value);

/** The portable context an action receives, the same shape a menu row sends. */
const notify = (control: Control, extension: InstalledExtension) => (value: unknown) =>
	void invokeAction(extension, control.action as string, {
		name: control.name,
		blockId: editorContext.value.selection.blockId,
		value,
	});

/**
 * A bound control with no action hands back nothing, and the wrapper's own
 * default reads and writes the block.
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
		// an unbound control owns no block property, so its own name identifies it
		propertyKey: control.bind?.attribute ?? control.bind?.style ?? control.name,
		placeholder: control.placeholder,
		options: control.options,
		min: control.min,
		max: control.max,
		step: control.step,
		...WIDGETS[control.control],
		...valueProps(control, extension),
	}),
	// the panel's search filter reads this, and the type requires it
	searchKeyWords: [sectionLabel, control.label, control.name].filter(Boolean).join(", "),
	condition: control.showWhen ? () => matches(control.showWhen, editorContext.value) : undefined,
});
