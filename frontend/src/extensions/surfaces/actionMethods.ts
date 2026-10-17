/**
 * Actions are the functions of an extension. The host calls them.
 */

import { toast } from "frappe-ui";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { fields, refuse, text } from "../bridge/params";

const actions = new Set<string>();

const keyOf = (extension: InstalledExtension, action: string) => `${extension.name}:${action}`;

const register = (params: unknown, extension: InstalledExtension) => {
	const key = keyOf(extension, text(fields(params).name, "name"));
	if (!actions.has(key)) bridge.registerTeardown(extension.name, () => actions.delete(key));
	actions.add(key);
};

const unregister = (params: unknown, extension: InstalledExtension) => {
	const key = keyOf(extension, text(fields(params).name, "name"));
	if (!actions.delete(key)) throw refuse(`No action is registered under "${key}".`, "unknown_item");
};

/** Fails if no live action has the name, or if the handler fails. The caller reports it. */
const runAction = (extension: InstalledExtension, action: string, context: Record<string, unknown> = {}) => {
	const channel = actions.has(keyOf(extension, action)) && bridge.getEntryChannel(extension.name);
	if (!channel)
		throw refuse(`No live action is registered under "${keyOf(extension, action)}".`, "unknown_item");
	return channel.call("action.invoke", { action, context });
};

/**
 * For a click. Nothing waits for the result, so it shows a toast and logs
 * both names. So a user sees a message, and an author sees a stack.
 */
export const invokeAction = async (
	extension: InstalledExtension,
	action: string,
	context: Record<string, unknown> = {},
) => {
	try {
		await runAction(extension, action, context);
	} catch (error) {
		toast.error(`${extension.label} failed to run "${action}".`);
		console.error(`Extension "${extension.name}" failed while running "${action}"`, error);
	}
};

const run = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return runAction(extension, text(sent.name, "name"), fields(sent.context));
};

export const actionMethods: MethodTable = {
	// the handler runs in the frame of the extension. So these methods need no permission
	"actions.register": { needs: null, run: register },
	"actions.unregister": { needs: null, run: unregister },
	"actions.run": { needs: null, run },
};
