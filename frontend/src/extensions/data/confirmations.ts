/**
 * The question that Builder asks before an extension makes or removes a doctype.
 */

import { ref } from "vue";
import { bridge } from "../bridge/bridge";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

export type SchemaAct = "create" | "delete" | "remove field" | "change access";

export type ExtensionPrompt = {
	extension: InstalledExtension;
	doctype: string;
	act: SchemaAct;
	/** The field to remove, or the roles that get access. */
	detail?: string;
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

/**
 * How many times each extension stopped. A queued question keeps the count from
 * when it was asked. If the count changed, the extension stopped, so the
 * question gets no without a dialog. A restarted extension can still ask.
 */
const stops = new Map<string, number>();

const stopCount = (extension: string) => stops.get(extension) ?? 0;

const hookTeardown = (extension: InstalledExtension) => {
	if (hooked.has(extension.name)) return;
	hooked.add(extension.name);
	bridge.registerTeardown(extension.name, () => {
		hooked.delete(extension.name);
		stops.set(extension.name, stopCount(extension.name) + 1);
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
 * The Frappe gate, create permission on `DocType`, only says that the user
 * *can* do the act by hand. It does not say that the user wants this extension
 * to do it. So Builder names the act each time.
 */
export const confirmSchema = (
	extension: InstalledExtension,
	doctype: string,
	act: SchemaAct,
	detail?: string,
) => {
	hookTeardown(extension);
	const asked = stopCount(extension.name);
	return enqueue(() =>
		stopCount(extension.name) === asked ? ask({ extension, doctype, act, detail }) : Promise.resolve(false),
	);
};
