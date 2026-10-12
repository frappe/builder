/** `builder.context`: the snapshot of the editor, and the fields to watch. */

import { getChannel } from "../connect";
import { call } from "./call";

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
		// a call, not a registration. Any frame can subscribe. The host pushes to
		// each frame of the extension, so a panel gets what it asked for
		void call("context.subscribe", { fields });
		return stop;
	},
};
