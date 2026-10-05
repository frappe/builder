/**
 * `builder.<surface>.<verb>` over one call.
 *
 * Nothing is validated here. The host validates every parameter, and a
 * copy of a rule on this side would be a second thing to keep in step.
 */

import { getChannel } from "./connect";

/** An imperative call. Any frame may make one. */
const call = (method: string, params?: unknown) => getChannel().call(method, params);

export type ContextField =
	"selection" | "breakpoint" | "editingMode" | "readOnly" | "isAIEnabled" | "page" | "site";

export type ContextHandler = (context: Record<string, unknown>) => void;

export const context = {
	/** The whole snapshot, once. For startup. */
	get: () => call("context.get") as Promise<Record<string, unknown>>,

	/**
	 * Names the fields this extension cares about, so the host sends nothing else
	 * and only when one of them changes.
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
