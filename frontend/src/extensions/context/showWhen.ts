/**
 * The rule that an extension declares, and the matcher that the host runs when it renders.
 *
 * A `condition` runs in a computed. It must answer at once. An extension runs
 * in a different realm, where each answer is asynchronous. So the extension
 * gives a rule about the host state, and the host checks the rule.
 *
 * The host owns the keys. Each key names a field of the snapshot. So an
 * author sees the same name in both places. Add keys one at a time. It is easy
 * to add a key later. It is difficult to remove one.
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
	const unknown = Object.keys(rule ?? {}).filter((key) => !(key in READERS));
	if (!unknown.length) return;

	throw new ChannelCallError({
		message: `Unknown ${field} keys: ${unknown.join(", ")}. Known keys: ${Object.keys(READERS).join(", ")}.`,
		code: "unknown_rule_key",
	});
};
