/**
 * Every block field that an extension can write, in one table.
 *
 * A field has the name that `block.get` returns, so an extension reads a
 * block, changes a field, and writes it back. A new block field is one row.
 *
 * Builder's bookkeeping (`blockId`, the component links, the parent) is not
 * here, and neither is `clientScript`: the editor cannot show or edit it, so
 * code for a page goes in a `Builder Client Script` record.
 */

import type Block from "@/block";
import type { Breakpoint } from "frappe-builder-extension-sdk/types";
import { anyText, refuse } from "../bridge/params";
import {
	asObject,
	readDataKey,
	readDynamicValues,
	readFlag,
	readProps,
	readVisibility,
} from "./blockBindings";
import { readAttributes, readElement, readHTML } from "./safeMarkup";

type Read = { element: string; field: string };
type Field = {
	read: (value: unknown, context: Read) => unknown;
	write: (block: Block, value: any, breakpoint?: Breakpoint) => void;
};
type StyleMap = Record<string, string | number | null>;

/** `null` and `""` remove a style. `setStyle` has the same rule. */
const readStyles = (value: unknown, field: string): StyleMap => {
	Object.entries(asObject(value, field)).forEach(([style, sent]) => {
		if (sent !== null && typeof sent !== "string" && typeof sent !== "number") {
			throw refuse(`"${field}.${style}" must be a string, a number or null.`, "invalid_params");
		}
	});
	return value as StyleMap;
};

const readClasses = (value: unknown, field: string) => {
	if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
		throw refuse(`"${field}" must be a list of strings.`, "invalid_params");
	}
	return value as string[];
};

/** A style map merges into one breakpoint. `styles` takes the one the user sees, unless `breakpoint` names one. */
const stylesOf = (fixed?: Breakpoint): Field => ({
	read: (value, { field }) => readStyles(value, field),
	write: (block, styles: StyleMap, breakpoint) =>
		Object.entries(styles).forEach(([style, value]) => block.setStyle(style, value, fixed ?? breakpoint)),
});

/** A map merges into the current one. A `null` value removes that key. */
const attributesOf = (write: (block: Block, name: string, value: string | undefined) => void): Field => ({
	read: (value, { element, field }) => readAttributes(value, element, field),
	write: (block, map: Record<string, string | undefined>) =>
		Object.entries(map).forEach(([name, value]) => write(block, name, value)),
});

/** In the order they are written. `element` is first, so the attribute checks use the new tag. */
const FIELDS: Record<string, Field> = {
	element: { read: (value, { field }) => readElement(value, field), write: (block, value) => (block.element = value) },
	attributes: attributesOf((block, name, value) => block.setAttribute(name, value)),
	customAttributes: attributesOf((block, name, value) => {
		if (value === undefined) delete block.customAttributes[name];
		else block.customAttributes[name] = value;
	}),
	classes: { read: (value, { field }) => readClasses(value, field), write: (block, value) => (block.classes = value) },
	innerHTML: { read: (value, { field }) => readHTML(value, field), write: (block, value) => block.setInnerHTML(value) },
	styles: stylesOf(),
	baseStyles: stylesOf("desktop"),
	tabletStyles: stylesOf("tablet"),
	mobileStyles: stylesOf("mobile"),
	blockName: { read: (value, { field }) => anyText(value, field), write: (block, value) => (block.blockName = value) },
	isRepeaterBlock: {
		read: (value, { field }) => readFlag(value, field),
		write: (block, value) => (block.isRepeaterBlock = value),
	},
	// a cleared data key is `{}`, as "Remove Collection" leaves it. The server reads a key from it
	dataKey: { read: (value, { field }) => readDataKey(value, field), write: (block, value) => (block.dataKey = value ?? {}) },
	dynamicValues: {
		read: (value, { field }) => readDynamicValues(value, field),
		write: (block, value) => (block.dynamicValues = value),
	},
	visibilityCondition: {
		read: (value, { field }) => readVisibility(value, field),
		write: (block, value) => (block.visibilityCondition = value ?? undefined),
	},
	props: { read: (value, { field }) => readProps(value, field), write: (block, value) => (block.props = value) },
};

export type BlockFields = Record<string, unknown>;

/**
 * Reads the fields that `sent` names, and checks each one. Nothing is written,
 * so a refused call leaves the page as it was. `params` are the other keys
 * that the method itself takes, such as `blockId`.
 */
export const readBlockFields = (sent: Record<string, unknown>, element: string, params: string[], prefix = "") => {
	const unknown = Object.keys(sent).find((key) => !(key in FIELDS) && !params.includes(key));
	if (unknown) {
		throw refuse(`"${prefix}${unknown}" is not a block field. Use: ${Object.keys(FIELDS).join(", ")}.`, "invalid_params");
	}
	const read: BlockFields = {};
	const tag = sent.element === undefined ? element : (FIELDS.element.read(sent.element, { element, field: `${prefix}element` }) as string);
	for (const name of Object.keys(FIELDS)) {
		if (sent[name] === undefined) continue;
		read[name] = FIELDS[name].read(sent[name], { element: tag, field: `${prefix}${name}` });
	}
	return read;
};

export const writeBlockFields = (block: Block, read: BlockFields, breakpoint?: Breakpoint) =>
	Object.entries(read).forEach(([name, value]) => FIELDS[name].write(block, value, breakpoint));
