/**
 * The questions that Builder asks before an extension does an act that cannot be undone.
 *
 * Each question names one act: to make or remove a doctype, or to put a
 * script on a page. It records nothing, because there is no lasting
 * permission. The next act asks again. The Frappe permission still decides if
 * this user can do the act. No call here gives more access.
 */

import { ref } from "vue";
import { bridge } from "../bridge/bridge";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

export type PromptKind = "schema" | "script";

export type ExtensionPrompt = {
	kind: PromptKind;
	extension: InstalledExtension;
	/** The doctype of a schema prompt, or the page route of a script prompt. */
	subject: string;
	sensitive: boolean;
	/** For a schema prompt: the verb, as the dialog shows it. */
	act?: "create" | "delete";
};

/** `ExtensionConfirmDialog.vue` reads this. Only one prompt is open at a time, so this is one ref. */
export const pendingPrompt = ref<ExtensionPrompt | null>(null);

let answer: ((allowed: boolean) => void) | null = null;

/**
 * The answer of the user, from the dialog. A dismiss counts as no. Browser
 * permission prompts do the same. A question with no answer is not a yes.
 */
export const answerPrompt = (allowed: boolean) => {
	const settle = answer;
	answer = null;
	pendingPrompt.value = null;
	settle?.(allowed);
};

/** The extensions that already have a teardown hook. So a second question adds no second hook. */
const hooked = new Set<string>();

const hookTeardown = (extension: InstalledExtension) => {
	if (hooked.has(extension.name)) return;
	hooked.add(extension.name);
	bridge.registerTeardown(extension.name, () => {
		hooked.delete(extension.name);
		// remove the prompt when its extension stops. Otherwise it asks for an extension that is gone
		if (pendingPrompt.value?.extension.name === extension.name) answerPrompt(false);
	});
};

/**
 * One dialog at a time, in the order of the requests.
 *
 * Two frames of one extension can ask at the same time. So can two extensions.
 * The queue stops the second dialog from covering the first. The second
 * request waits. It is not refused.
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
 * Asks the user to allow one act on the schema. It remembers nothing.
 *
 * To make a table and to remove a table are the two most serious acts in this
 * API. The Frappe gate, create permission on `DocType`, only says that the user
 * *can* do the act by hand. It does not say that the user wants this extension
 * to do it. So Builder names the act each time.
 *
 * `schemaMethods.ts` is the only caller.
 */
export const confirmSchema = (extension: InstalledExtension, doctype: string, act: "create" | "delete") => {
	hookTeardown(extension);
	return enqueue(() =>
		ask({ kind: "schema", extension, subject: doctype, act, sensitive: act === "delete" }),
	);
};

/**
 * Asks the user to let this extension put a script on one page. It remembers nothing.
 *
 * A client script is JavaScript on a public page, on the origin of the site.
 * After it is added, nothing limits it. The Frappe gate, write permission on
 * `Builder Client Script`, only says that the user can add one by hand. It
 * does not say that the user wants this extension to do it.
 *
 * So Builder names the page each time that an extension makes a script. It
 * does not ask again when the extension changes its own script. The user
 * already let this extension run code on this page.
 *
 * `pageMethods.ts` is the only caller.
 */
export const confirmPageScript = (extension: InstalledExtension, route: string) => {
	hookTeardown(extension);
	return enqueue(() => ask({ kind: "script", extension, subject: route, sensitive: true }));
};
