/** `builder.actions`, and the helpers that turn a function action into a name. */

import { setHandler, deleteHandler, type ActionHandler } from "../actions";
import { getActiveSlot } from "../slots";
import { call, callFromEntryOnly } from "./call";

/**
 * A function, or the name of an action from a different registration.
 *
 * A function cannot go through the port. The SDK keeps it in this frame and
 * sends the name of the item. A string names an action that a different call
 * registered. A frame that is not the entry frame must use a string.
 */
export type ActionRef = string | ActionHandler;

/** Keeps a handler in this frame and sends its name to the host. Entry frame only. */
const registerAction = (name: string, handler: ActionHandler) => {
	if (getActiveSlot() === "main") setHandler(name, handler);
	return callFromEntryOnly("actions.register", { name });
};

/** Replaces a function action with its name, because a function cannot be cloned. */
export const resolveAction = <T extends { name: string; action?: ActionRef }>(item: T, prefix = ""): T => {
	if (typeof item.action !== "function") return item;
	const name = `${prefix}${item.name}`;
	void registerAction(name, item.action);
	return { ...item, action: name };
};

export const actions = {
	/**
	 * The handler stays in this frame. The host gets only the name.
	 *
	 * Only the entry frame keeps and names the handler. So the host always
	 * calls the frame that lives longest.
	 */
	register: (name: string, handler: ActionHandler) => registerAction(name, handler),
	unregister: (name: string) => {
		if (getActiveSlot() !== "main") return Promise.resolve();
		deleteHandler(name);
		return call("actions.unregister", { name });
	},
	/** Runs an action of this extension from any of its frames. */
	run: (name: string, context?: Record<string, unknown>) => call("actions.run", { name, context }),
};
