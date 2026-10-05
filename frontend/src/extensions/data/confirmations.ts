/**
 * The questions Builder asks before an extension does something it cannot undo.
 *
 * Each one names one act — creating or dropping a doctype, putting a script on a
 * page — and records nothing, because there is no standing permission to
 * remember: the next act asks again. Frappe's own permission still decides
 * whether this user may do it, and no call in this tree widens it.
 */

import { ref } from "vue";
import { bridge } from "../host/bridge";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

export type PromptKind = "schema" | "script";

export type ExtensionPrompt = {
	kind: PromptKind;
	extension: InstalledExtension;
	/** The doctype a schema prompt names. The page route a script prompt names. */
	subject: string;
	sensitive: boolean;
	/** For a schema prompt: the verb, in the words the dialog uses. */
	act?: "create" | "delete";
};

/** Read by `ExtensionConfirmDialog.vue`. One prompt stands at a time, so this is a single ref. */
export const pendingPrompt = ref<ExtensionPrompt | null>(null);

let answer: ((allowed: boolean) => void) | null = null;

/**
 * The user's answer, from the dialog. Dismissing it counts as no, which is what
 * every browser permission prompt does and the only honest reading of a
 * question nobody answered.
 */
export const answerPrompt = (allowed: boolean) => {
	const settle = answer;
	answer = null;
	pendingPrompt.value = null;
	settle?.(allowed);
};

/** Which extensions already have a teardown hook, so asking twice adds one hook. */
const hooked = new Set<string>();

const hookTeardown = (extension: InstalledExtension) => {
	if (hooked.has(extension.name)) return;
	hooked.add(extension.name);
	bridge.registerTeardown(extension.name, () => {
		hooked.delete(extension.name);
		// a prompt outliving the extension that asked would ask on behalf of nobody
		if (pendingPrompt.value?.extension.name === extension.name) answerPrompt(false);
	});
};

/**
 * One dialog at a time, in the order the requests arrived.
 *
 * Two frames of one extension can ask at once, and so can two extensions. A
 * queue is what stops the second request drawing over the first, and it costs a
 * wait rather than a refusal.
 */
let queue: Promise<unknown> = Promise.resolve();

const enqueue = <T>(task: () => Promise<T>): Promise<T> => {
	const next = queue.then(task, task);
	queue = next.catch(() => undefined);
	return next;
};

const ask = (request: ExtensionPrompt) =>
	new Promise<boolean>((resolve) => {
		answer = resolve;
		pendingPrompt.value = request;
	});

/**
 * Asks the user to allow one act on the schema, and remembers nothing.
 *
 * Creating a table and dropping one are the two most consequential things this
 * API can do, and Frappe's own gate — create permission on `DocType` — only
 * says the user *could* do it by hand, not that they meant this extension to.
 * So the act is named, once, each time.
 *
 * Exported for `schemaMethods.ts`, which is the only caller.
 */
export const confirmSchema = (extension: InstalledExtension, doctype: string, act: "create" | "delete") => {
	hookTeardown(extension);
	return enqueue(() =>
		ask({ kind: "schema", extension, subject: doctype, act, sensitive: act === "delete" }),
	);
};

/**
 * Asks the user to let this extension put a script on one page, and remembers
 * nothing.
 *
 * A client script is JavaScript on a public page at the site's own origin, and
 * nothing bounds it once it lands. Frappe's own gate — write permission on
 * `Builder Client Script` — says the user could add one by hand, not that they
 * meant this extension to. So the page is named, once, each time a script is
 * created. Rewriting a script the extension already owns asks again for
 * nothing: the user allowed this extension to run code on this page, and it is
 * the same code's next version.
 *
 * Exported for `pageMethods.ts`, which is the only caller.
 */
export const confirmPageScript = (extension: InstalledExtension, route: string) => {
	hookTeardown(extension);
	return enqueue(() => ask({ kind: "script", extension, subject: route, sensitive: true }));
};
