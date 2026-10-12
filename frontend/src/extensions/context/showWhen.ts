/**
 * The rule that an extension declares, and the matcher that the host runs when it renders.
 */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import type { Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/** The rule keys, with one reader for each key. Add new keys only here. */
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

/**
 * All keys must match. No rule is a match. So an item with no rule shows
 * where the flag of its owner allows.
 *
 * The comparison is strict. So a value of the wrong type hides the item.
 */
export const matches = (rule: ShowWhenRule | undefined, context: EditorContext) =>
	!rule || Object.entries(rule).every(([key, wanted]) => READERS[key as RuleKey](context) === wanted);

/**
 * An unknown key causes an error at registration. The error names the key.
 * If the matcher ignored the key, the item would show in all places.
 */
export const assertRule = (rule: ShowWhenRule | undefined, field = "showWhen") => {
	// not `in`: it also accepts inherited keys, such as `__proto__`, that have no reader
	const unknown = Object.keys(rule ?? {}).filter((key) => !Object.hasOwn(READERS, key));
	if (!unknown.length) return;

	throw new ChannelCallError({
		message: `Unknown ${field} keys: ${unknown.join(", ")}. Known keys: ${Object.keys(READERS).join(", ")}.`,
		code: "unknown_rule_key",
	});
};
