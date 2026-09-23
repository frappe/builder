/**
 * Actions: the functions an extension owns, and the host calls back into.
 *
 * A descriptor cannot carry a function across `postMessage`, so an extension
 * names an action and the host turns that name into a function. The
 * handler itself never leaves the frame. Invoking one is the only path where
 * the host calls the extension, rather than the other way round.
 *
 * An action is scoped to the extension that registered it, so there is no
 * shared namespace and no extension can invoke another's action.
 *
 * Only the entry frame should register an action, because any other frame may
 * be closed while the action is still on a descriptor. The host cannot tell
 * which frame called, so the SDK refuses it where the slot is known — the same
 * reasoning 1.12 applies to origin checks.
 */

import { toast } from "frappe-ui";
import { bridge } from "../host/bridge";
import type { MethodTable } from "../host/capabilities";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { fields, refuse, text } from "../params";

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
 * An action that resolves to nothing rejects, raises a toast and logs both
 * names, so a user sees a message and an author sees a stack.
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
	// the handler runs in the extension's own frame, so nothing here needs a grant
	"actions.register": { needs: null, run: register },
	"actions.unregister": { needs: null, run: unregister },
	"actions.run": { needs: null, run },
};
