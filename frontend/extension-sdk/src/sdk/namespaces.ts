/**
 * `builder.<surface>.<verb>` over one call.
 *
 * Registrations are declarations, written at module scope. Every frame of an
 * extension imports the same module, so every frame reads them — which is what
 * lets a panel tab declare the document it loads in the same breath as the tab
 * itself, even though the two are used in different frames.
 *
 * Only the entry frame tells the host. A declaration read in a panel frame
 * records what that frame needs locally and sends nothing, so the host hears
 * each registration once however many frames are open.
 *
 * Nothing is validated here. The host validates every parameter, and a
 * copy of a rule on this side would be a second thing to keep in step.
 */

import { holdAction, releaseAction, type ActionHandler } from "./actions";
import { getChannel } from "./connect";
import { getActiveSlot } from "./slots";

/** An imperative call. Any frame may make one: `update` and `run` are not declarations. */
const call = (method: string, params?: unknown) => getChannel().call(method, params);

/**
 * A declaration. The host hears it from the entry frame only.
 *
 * A refusal is logged as well as returned, because a declaration at module scope
 * is usually not awaited, and a silently rejected registration is a surface that
 * never appears with nothing to explain it.
 *
 * A method this Builder does not have is a version gap, not a mistake. An
 * extension ships on its own schedule, so it loses that one surface and keeps
 * the rest, and the warning says which Builder is behind rather than blaming
 * the extension.
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
 * A function, or the name of an action registered elsewhere.
 *
 * A function cannot cross the port, so the SDK holds it in this frame and sends
 * the item's own name. A string names an action another call registered, which
 * is what a frame other than the entry one has to use.
 */
export type ActionRef = string | ActionHandler;

/** Holds a handler in this frame and tells the host its name. The entry frame only. */
const registerAction = (name: string, handler: ActionHandler) => {
	if (getActiveSlot() === "main") holdAction(name, handler);
	return declare("actions.register", { name });
};

/** Swaps a function action for the name it is held under, because a function cannot be cloned. */
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
	/** A function, or the name of an action this extension registered. */
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
	/** The whole snapshot, once. For startup. */
	get: () => call("context.get") as Promise<Record<string, unknown>>,

	/**
	 * Names the fields this extension cares about, so the host sends nothing else
	 * and only when one of them changes.
	 *
	 * Use it for a fact no rule can state — `isSVG` is in the snapshot but is not
	 * a rule key — and push the answer back with `update`. Use `showWhen` for
	 * anything the rule vocabulary already covers: it costs no messages.
	 */
	subscribe: (fields: ContextField[], handler: ContextHandler) => {
		// the host holds one subscription per extension, so a push carries every
		// field any call site named. This handler hears only its own.
		let seen = "";
		const stop = getChannel().listen("context", (payload) => {
			const context = payload as Record<string, unknown>;
			const mine = JSON.stringify(fields.map((field) => context[field]));
			if (mine === seen) return;
			seen = mine;
			handler(context);
		});
		// a call, not a declaration: any frame may subscribe, and the host pushes
		// to every frame of the extension, so a panel hears what a panel asked for
		void call("context.subscribe", { fields });
		return stop;
	},
};

export const actions = {
	/**
	 * The handler stays in this frame, and the host learns only the name.
	 *
	 * Only the entry frame holds and names it, so the host always calls the frame
	 * that outlives the others.
	 */
	register: (name: string, handler: ActionHandler) => registerAction(name, handler),
	unregister: (name: string) => {
		if (getActiveSlot() !== "main") return Promise.resolve();
		releaseAction(name);
		return call("actions.unregister", { name });
	},
	/** Runs an action this extension owns, from any of its frames. */
	run: (name: string, context?: Record<string, unknown>) => call("actions.run", { name, context }),
};
