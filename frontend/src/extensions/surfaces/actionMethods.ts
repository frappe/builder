/**
 * Actions are the functions of an extension. The host calls them.
 *
 * A descriptor cannot send a function through `postMessage`. So an extension
 * names an action, and the host changes that name into a function. The handler
 * stays in the frame. This is the only place where the host calls the
 * extension. In all other places, the extension calls the host.
 *
 * Each action belongs to the extension that registered it. There is no shared
 * namespace. No extension can run the action of a different extension.
 *
 * Only the entry frame must register an action. A different frame can close
 * while a descriptor still shows the action. The host cannot know which frame
 * called. So the SDK makes the check, because it knows the slot. The origin
 * check uses the same approach.
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

/**
 * If no action has the name, the call fails. It shows a toast and logs both
 * names. So a user sees a message, and an author sees a stack.
 */
export const invokeAction = async (
	extension: InstalledExtension,
	action: string,
	context: Record<string, unknown> = {},
) => {
	const channel = actions.has(keyOf(extension, action)) && bridge.getEntryChannel(extension.name);
	if (!channel) {
		toast.error(`${extension.label} could not run "${action}".`);
		console.error(`Extension "${extension.name}" has no live action named "${action}"`);
		return;
	}

	try {
		return await channel.call("action.invoke", { action, context });
	} catch (error) {
		toast.error(`${extension.label} failed to run "${action}".`);
		console.error(`Extension "${extension.name}" failed while running "${action}"`, error);
	}
};

const run = (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	return invokeAction(extension, text(sent.name, "name"), fields(sent.context));
};

export const actionMethods: MethodTable = {
	// the handler runs in the frame of the extension. So these methods need no permission
	"actions.register": { needs: null, run: register },
	"actions.unregister": { needs: null, run: unregister },
	"actions.run": { needs: null, run },
};
