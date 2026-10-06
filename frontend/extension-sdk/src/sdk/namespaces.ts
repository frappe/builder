/**
 * Each `builder.<surface>.<verb>` sends one call.
 *
 * Registrations are declarations. Write them at module scope. Each frame of
 * an extension imports the same module, so each frame reads them. So a panel
 * tab can name its document next to the tab itself. The tab and the document
 * are in different frames.
 *
 * Only the entry frame sends a declaration to the host. A panel frame keeps
 * what it needs and sends nothing. So the host gets each registration one
 * time, for any number of open frames.
 *
 * This file does not validate. The host validates each parameter. A copy of a
 * rule here would be a second rule to keep the same.
 */

import { holdAction, releaseAction, type ActionHandler } from "./actions";
import { getChannel } from "./connect";
import { getActiveSlot } from "./slots";

/** A direct call. Any frame can make one. `update` and `run` are not declarations. */
const call = (method: string, params?: unknown) => getChannel().call(method, params);

/**
 * A declaration. The host gets it from the entry frame only.
 *
 * This function logs a refusal and also returns it. Authors usually do not
 * await a declaration at module scope. A silent refusal gives a surface that
 * does not show, with no message.
 *
 * A method that this Builder does not have shows a version gap, not an error.
 * An extension has its own release schedule. It loses only that surface. The
 * warning tells that Builder is older than the extension.
 */
export const declare = (method: string, params?: unknown) => {
	if (getActiveSlot() !== "main") return Promise.resolve();

	const sent = call(method, params);
	sent.catch((error) => {
		if ((error as { code?: string }).code === "unknown_method") {
			console.warn(`[builder] this Builder has no "${method}", so that surface is skipped`);
			return;
		}
		console.error(`[builder] "${method}" was refused`, error);
	});
	return sent;
};

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
	if (getActiveSlot() === "main") holdAction(name, handler);
	return declare("actions.register", { name });
};

/** Replaces a function action with its name, because a function cannot be cloned. */
const resolveAction = <T extends { name: string; action?: ActionRef }>(item: T): T => {
	if (typeof item.action !== "function") return item;
	void registerAction(item.name, item.action);
	return { ...item, action: item.name };
};

export type ShowWhen = Record<string, unknown>;

export type ToolbarRegistration = {
	name: string;
	region: "left" | "center" | "right";
	icon: string;
	label?: string;
	tooltip?: string;
	/** A function, or the name of an action that this extension registered. */
	action?: ActionRef;
	badge?: string | number | null;
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
	enableWhen?: ShowWhen;
};

export type ItemPatch = {
	visible?: boolean;
	enabled?: boolean;
	label?: string;
	icon?: string;
	tooltip?: string;
	badge?: string | number | null;
};

export const toolbar = {
	register: (registration: ToolbarRegistration) => declare("toolbar.register", resolveAction(registration)),
	unregister: (name: string) => call("toolbar.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("toolbar.update", { name, patch }),
};

export type ContextField =
	"selection" | "breakpoint" | "editingMode" | "readOnly" | "isAIEnabled" | "page" | "site";

export type ContextHandler = (context: Record<string, unknown>) => void;

export const context = {
	/** The full snapshot, one time. Use it at startup. */
	get: () => call("context.get") as Promise<Record<string, unknown>>,

	/**
	 * Names the fields that this extension watches. The host sends only these
	 * fields, and only when one of them changes.
	 *
	 * Use it for a fact that no rule can state. For example, `isSVG` is in the
	 * snapshot, but it is not a rule key. Send the result back with `update`.
	 * For all other cases, use `showWhen`. It sends no messages.
	 */
	subscribe: (fields: ContextField[], handler: ContextHandler) => {
		// the host keeps one subscription for each extension. So each push has
		// all the fields that any caller named. This handler gets only its own fields
		let seen = "";
		const stop = getChannel().listen("context", (payload) => {
			const context = payload as Record<string, unknown>;
			const mine = JSON.stringify(fields.map((field) => context[field]));
			if (mine === seen) return;
			seen = mine;
			handler(context);
		});
		// a call, not a declaration. Any frame can subscribe. The host pushes to
		// each frame of the extension, so a panel gets what it asked for
		void call("context.subscribe", { fields });
		return stop;
	},
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
		releaseAction(name);
		return call("actions.unregister", { name });
	},
	/** Runs an action of this extension from any of its frames. */
	run: (name: string, context?: Record<string, unknown>) => call("actions.run", { name, context }),
};
