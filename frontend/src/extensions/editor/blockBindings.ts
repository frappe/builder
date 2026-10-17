/**
 * The readers of the fields that connect a block to data: a repeater, its data
 * key, the dynamic values of each block, a visibility condition, and props.
 * `blockFields.ts` names each field once and uses these.
 */

import type Block from "@/block";
import { anyText, fields, oneOf, refuse, text } from "../bridge/params";

const TYPES = ["key", "attribute", "style"] as const;
const SOURCES = ["dataScript", "props", "componentData"] as const;

/** A block that binds more values than this is a mistake, not a design. */
const MAX_DYNAMIC_VALUES = 50;


const optionalSource = (value: unknown, field: string) =>
	value === undefined ? undefined : oneOf(value, SOURCES, field);

/** `type` and `property` are optional, as on a repeater, which needs only `key`. */
export const readDataKey = (value: unknown, field: string): BlockDataKey | null | undefined => {
	if (value === undefined || value === null) return value;
	const sent = asObject(value, field);
	return {
		key: text(sent.key, `${field}.key`),
		...(sent.type !== undefined && { type: oneOf(sent.type, TYPES, `${field}.type`) }),
		...(sent.property !== undefined && { property: text(sent.property, `${field}.property`) }),
		...(sent.comesFrom !== undefined && { comesFrom: optionalSource(sent.comesFrom, `${field}.comesFrom`) }),
	};
};

/** Each entry binds one property, so each entry needs all three parts. */
const readDynamicValue = (value: unknown, field: string): BlockDataKey => {
	const sent = asObject(value, field);
	return {
		key: text(sent.key, `${field}.key`),
		type: oneOf(sent.type, TYPES, `${field}.type`),
		property: text(sent.property, `${field}.property`),
		comesFrom: optionalSource(sent.comesFrom, `${field}.comesFrom`) ?? "dataScript",
	};
};

export const readDynamicValues = (value: unknown, field: string) => {
	if (value === undefined) return undefined;
	if (!Array.isArray(value) || value.length > MAX_DYNAMIC_VALUES) {
		throw refuse(`"${field}" must be a list of ${MAX_DYNAMIC_VALUES} entries or less.`, "invalid_params");
	}
	return value.map((entry, index) => readDynamicValue(entry, `${field}[${index}]`));
};

export const readVisibility = (value: unknown, field: string): BlockVisibilityCondition | null | undefined => {
	if (value === undefined || value === null) return value;
	const sent = asObject(value, field);
	return { key: text(sent.key, `${field}.key`), comesFrom: optionalSource(sent.comesFrom, `${field}.comesFrom`) };
};

export const readFlag = (value: unknown, field: string) => {
	if (value === undefined || typeof value === "boolean") return value;
	throw refuse(`"${field}" must be true or false.`, "invalid_params");
};

export const asObject = (value: unknown, field: string) => {
	if (typeof value !== "object" || value === null || Array.isArray(value)) {
		throw refuse(`"${field}" must be an object.`, "invalid_params");
	}
	return fields(value);
};

/**
 * A repeater repeats its children, so only a container that is not the page
 * root can be one. It also needs the key of the list that it repeats.
 */
export const assertCanRepeat = (bindings: Record<string, unknown>, block: Block) => {
	// a patch that leaves the loop alone must not fail on an old repeater
	if (!("isRepeaterBlock" in bindings) && !("dataKey" in bindings)) return;
	const isRepeater = (bindings.isRepeaterBlock as boolean | undefined) ?? block.isRepeater();
	if (!isRepeater) return;
	if (block.isRoot() || !block.canHaveChildren()) {
		throw refuse(`A <${block.getElement()}> block cannot be a repeater.`, "invalid_params");
	}
	const dataKey = (bindings.dataKey === undefined ? block.dataKey : bindings.dataKey) as BlockDataKey | null;
	if (!dataKey?.key) throw refuse(`A repeater needs "dataKey.key", the list that it repeats.`, "invalid_params");
};

const readProp = (value: unknown, field: string) => {
	const sent = asObject(value, field);
	const unknown = Object.keys(sent).find((key) => !PROP_KEYS.has(key));
	if (unknown) throw refuse(`"${field}.${unknown}" is not a prop setting.`, "invalid_params");
	return {
		...(sent.label !== undefined && { label: anyText(sent.label, `${field}.label`) }),
		isDynamic: readFlag(sent.isDynamic, `${field}.isDynamic`) ?? false,
		isPassedDown: readFlag(sent.isPassedDown, `${field}.isPassedDown`) ?? false,
		...(sent.isStandard !== undefined && { isStandard: readFlag(sent.isStandard, `${field}.isStandard`) }),
		comesFrom: sent.comesFrom == null ? null : oneOf(sent.comesFrom, SOURCES, `${field}.comesFrom`),
		value: sent.value === undefined || sent.value === null ? null : anyText(sent.value, `${field}.value`),
		...(sent.propOptions !== undefined && { propOptions: asObject(sent.propOptions, `${field}.propOptions`) }),
	};
};

const PROP_KEYS = new Set(["label", "isDynamic", "isPassedDown", "comesFrom", "value", "isStandard", "propOptions"]);

/** The props of a block, as the Props panel keeps them. The whole map is replaced. */
export const readProps = (value: unknown, field: string) =>
	Object.fromEntries(Object.entries(asObject(value, field)).map(([name, prop]) => [name, readProp(prop, `${field}.${name}`)]));
