/**
 * Each `builder.<surface>.<verb>` sends one call. Put registrations at module scope.
 * Only the entry frame sends them. The host checks the parameters.
 */

import { setHandler, deleteHandler, type ActionHandler } from "./actions";
import { getChannel } from "./connect";
import { getActiveSlot } from "./slots";

/** A direct call. Any frame can make one. */
const call = (method: string, params?: unknown) => getChannel().call(method, params);

/**
 * A call that only the entry frame sends. In other frames, it does nothing.
 * It logs an error and returns it. An unknown method gives a warning about an older Builder.
 */
export const callFromEntryOnly = (method: string, params?: unknown) => {
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

/** A function, or the name of an action. A frame that is not the entry frame must use a name. */
export type ActionRef = string | ActionHandler;

/** Keeps a handler in this frame and sends its name to the host. Only for the entry frame. */
const registerAction = (name: string, handler: ActionHandler) => {
	if (getActiveSlot() === "main") setHandler(name, handler);
	return callFromEntryOnly("actions.register", { name });
};

/** Replaces a function with its name. A function cannot go through the port. */
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
	/** A function, or the name of an action of this extension. */
	action?: ActionRef;
	badge?: string | number | null;
	/** The position among the extension buttons. The Builder buttons stay at the right end. */
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
	register: (registration: ToolbarRegistration) =>
		callFromEntryOnly("toolbar.register", resolveAction(registration)),
	unregister: (name: string) => call("toolbar.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("toolbar.update", { name, patch }),
};

export type ContextField =
	"selection" | "breakpoint" | "editingMode" | "readOnly" | "isAIEnabled" | "page" | "site";

export type ContextHandler = (context: Record<string, unknown>) => void;

export const context = {
	/** Returns the full snapshot one time. Use it at startup. */
	get: () => call("context.get") as Promise<Record<string, unknown>>,

	/**
	 * Subscribes to fields. The host sends them when one of them changes.
	 * Use `showWhen` if a rule can do the same. It sends no messages.
	 */
	subscribe: (fields: ContextField[], handler: ContextHandler) => {
		// The host keeps one subscription for each extension. So a push can have more fields.
		// This handler gets only its own fields.
		let seen = "";
		const stop = getChannel().listen("context", (payload) => {
			const context = payload as Record<string, unknown>;
			const mine = JSON.stringify(fields.map((field) => context[field]));
			if (mine === seen) return;
			seen = mine;
			handler(context);
		});
		// Any frame can subscribe. The host pushes to each frame of the extension.
		void call("context.subscribe", { fields });
		return stop;
	},
};

export const actions = {
	/** Registers an action. The handler stays in the entry frame. The host gets only the name. */
	register: (name: string, handler: ActionHandler) => registerAction(name, handler),
	unregister: (name: string) => {
		if (getActiveSlot() !== "main") return Promise.resolve();
		deleteHandler(name);
		return call("actions.unregister", { name });
	},
	/** Runs an action of this extension from any frame. */
	run: (name: string, context?: Record<string, unknown>) => call("actions.run", { name, context }),
};
