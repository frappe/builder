/**
 * Actions are named functions of an extension. The host calls them in the entry frame.
 * An extension can run only its own actions.
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

/** Fails if there is no action with this name, or if the handler fails. */
const runAction = (extension: InstalledExtension, action: string, context: Record<string, unknown> = {}) => {
	const channel = actions.has(keyOf(extension, action)) && bridge.getEntryChannel(extension.name);
	if (!channel)
		throw refuse(`No live action is registered under "${keyOf(extension, action)}".`, "unknown_item");
	return channel.call("action.invoke", { action, context });
};

/** Runs an action for a click. If it fails, it shows a toast and logs the error. */
export const invokeAction = async (extension: InstalledExtension, action: string) => {
	try {
		await runAction(extension, action);
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
	// The handler runs in the frame. So these methods need no permission.
	"actions.register": { needs: null, run: register },
	"actions.unregister": { needs: null, run: unregister },
	"actions.run": { needs: null, run },
};
