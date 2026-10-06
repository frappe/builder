/**
 * The rule an extension declares, and the matcher the host runs at render.
 *
 * A `condition` runs inside a computed and must answer synchronously. An
 * extension lives in another realm, where every answer is asynchronous. So the
 * extension states a rule about host state, and the host answers it.
 *
 * The host owns the keys. Each names a field the snapshot already publishes,
 * so an author reads one spelling in both places. Grow this list one key
 * at a time. Adding a key later is cheap. Removing one is not.
 */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import type { Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/** The vocabulary itself: one reader per key, and the only place it grows. */
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
 * Every key must match. A missing rule matches, so an item with no rule shows
 * wherever its owner's flag allows.
 *
 * The comparison is strict, so a value of the wrong type hides the item rather
 * than showing it.
 */
export const matches = (rule: ShowWhenRule | undefined, context: EditorContext) =>
	!rule || Object.entries(rule).every(([key, wanted]) => READERS[key as RuleKey](context) === wanted);

/**
 * An unknown key raises at registration and names the key. An ignored key would
 * make the item show everywhere, which is the wrong way to fail.
 */
export const assertRule = (rule: ShowWhenRule | undefined, field = "showWhen") => {
	const unknown = Object.keys(rule ?? {}).filter((key) => !(key in READERS));
	if (!unknown.length) return;

	throw new ChannelCallError({
		message: `Unknown ${field} keys: ${unknown.join(", ")}. Known keys: ${Object.keys(READERS).join(", ")}.`,
		code: "unknown_rule_key",
	});
};
