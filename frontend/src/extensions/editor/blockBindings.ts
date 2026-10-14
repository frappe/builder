/**
 * The fields that connect a block to page data: a repeater, its data key, the
 * dynamic values of each block, and a visibility condition. They have the names
 * that `block.get` returns, so an extension reads the same shape that it writes.
 */

import type Block from "@/block";
import { anyText, fields, oneOf, refuse, text } from "../bridge/params";

const TYPES = ["key", "attribute", "style"] as const;
const SOURCES = ["dataScript", "props", "componentData"] as const;

/** A block that binds more values than this is a mistake, not a design. */
const MAX_DYNAMIC_VALUES = 50;

export type Bindings = {
	blockName?: string;
	isRepeaterBlock?: boolean;
	dataKey?: BlockDataKey | null;
	dynamicValues?: BlockDataKey[];
	visibilityCondition?: BlockVisibilityCondition | null;
};

const optionalSource = (value: unknown, field: string) =>
	value === undefined ? undefined : oneOf(value, SOURCES, field);

/** `type` and `property` are optional, as on a repeater, which needs only `key`. */
const readDataKey = (value: unknown, field: string): BlockDataKey | null | undefined => {
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

const readDynamicValues = (value: unknown, field: string) => {
	if (value === undefined) return undefined;
	if (!Array.isArray(value) || value.length > MAX_DYNAMIC_VALUES) {
		throw refuse(`"${field}" must be a list of ${MAX_DYNAMIC_VALUES} entries or less.`, "invalid_params");
	}
	return value.map((entry, index) => readDynamicValue(entry, `${field}[${index}]`));
};

const readVisibility = (value: unknown, field: string): BlockVisibilityCondition | null | undefined => {
	if (value === undefined || value === null) return value;
	const sent = asObject(value, field);
	return { key: text(sent.key, `${field}.key`), comesFrom: optionalSource(sent.comesFrom, `${field}.comesFrom`) };
};

const readFlag = (value: unknown, field: string) => {
	if (value === undefined || typeof value === "boolean") return value;
	throw refuse(`"${field}" must be true or false.`, "invalid_params");
};

const asObject = (value: unknown, field: string) => {
	if (typeof value !== "object" || value === null || Array.isArray(value)) {
		throw refuse(`"${field}" must be an object.`, "invalid_params");
	}
	return fields(value);
};

/** Only the fields that the patch names. So `Object.keys` tells if the patch binds anything. */
export const readBindings = (sent: Record<string, unknown>, prefix = ""): Bindings => {
	const read: Bindings = {
		blockName: sent.blockName === undefined ? undefined : anyText(sent.blockName, `${prefix}blockName`),
		isRepeaterBlock: readFlag(sent.isRepeaterBlock, `${prefix}isRepeaterBlock`),
		dataKey: readDataKey(sent.dataKey, `${prefix}dataKey`),
		dynamicValues: readDynamicValues(sent.dynamicValues, `${prefix}dynamicValues`),
		visibilityCondition: readVisibility(sent.visibilityCondition, `${prefix}visibilityCondition`),
	};
	return Object.fromEntries(Object.entries(read).filter(([, value]) => value !== undefined));
};

/**
 * A repeater repeats its children, so only a container that is not the page
 * root can be one. It also needs the key of the list that it repeats.
 */
export const assertCanRepeat = (bindings: Bindings, block: Block) => {
	// a patch that leaves the loop alone must not fail on an old repeater
	if (!("isRepeaterBlock" in bindings) && !("dataKey" in bindings)) return;
	const isRepeater = bindings.isRepeaterBlock ?? block.isRepeater();
	if (!isRepeater) return;
	if (block.isRoot() || !block.canHaveChildren()) {
		throw refuse(`A <${block.getElement()}> block cannot be a repeater.`, "invalid_params");
	}
	const dataKey = bindings.dataKey === undefined ? block.dataKey : bindings.dataKey;
	if (!dataKey?.key) throw refuse(`A repeater needs "dataKey.key", the list that it repeats.`, "invalid_params");
};

/** A cleared data key is `{}`, as "Remove Collection" leaves it. The server reads a key from it. */
export const writeBindings = (block: Block, { dataKey, ...rest }: Bindings) => {
	Object.assign(block, rest);
	if (dataKey !== undefined) block.dataKey = dataKey ?? {};
};
