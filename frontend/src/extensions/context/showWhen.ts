/**
 * The `showWhen` rule of an extension, and the code that checks it.
 * An extension cannot answer a `condition` at once. So it gives a rule, and the host checks it.
 */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import type { Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/** The rule keys, with one reader for each key. Add new keys here. */
const READERS = {
	isRoot: (context: EditorContext) => context.selection.isRoot,
	isText: (context: EditorContext) => context.selection.isText,
	isImage: (context: EditorContext) => context.selection.isImage,
	isHTML: (context: EditorContext) => context.selection.isHTML,
	isContainer: (context: EditorContext) => context.selection.isContainer,
	count: (context: EditorContext) => context.selection.count,
	breakpoint: (context: EditorContext) => context.breakpoint,
	readOnly: (context: EditorContext) => context.readOnly,
};

export type ShowWhenRule = {
	isRoot?: boolean;
	isText?: boolean;
	isImage?: boolean;
	isHTML?: boolean;
	isContainer?: boolean;
	count?: number;
	breakpoint?: Breakpoint;
	readOnly?: boolean;
};

type RuleKey = keyof typeof READERS;

/** Returns true if all keys match, or if there is no rule. The comparison is strict. */
export const matches = (rule: ShowWhenRule | undefined, context: EditorContext) =>
	!rule || Object.entries(rule).every(([key, wanted]) => READERS[key as RuleKey](context) === wanted);

/** Stops a rule with an unknown key. If not, the item shows in all places. */
export const assertRule = (rule: ShowWhenRule | undefined, field = "showWhen") => {
	// Do not use `in`. It also finds inherited keys, such as `__proto__`.
	const unknown = Object.keys(rule ?? {}).filter((key) => !Object.hasOwn(READERS, key));
	if (!unknown.length) return;

	throw new ChannelCallError({
		message: `Unknown ${field} keys: ${unknown.join(", ")}. Known keys: ${Object.keys(READERS).join(", ")}.`,
		code: "unknown_rule_key",
	});
};
