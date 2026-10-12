/** The two ways that a `builder.<surface>.<verb>` call reaches the host. */

import { getChannel } from "../connect";
import { getActiveSlot } from "../slots";

/** A direct call. Any frame can make one. `update` and `run` are not registrations. */
export const call = (method: string, params?: unknown) => getChannel().call(method, params);

/**
 * A call that only the entry frame sends. In other frames it does nothing.
 * Use it for registrations at module scope. Every frame runs that code, and
 * the host still gets each registration one time.
 *
 * This function logs a refusal and also returns it. Authors usually do not
 * await a registration at module scope. A silent refusal gives a surface that
 * does not show, with no message.
 *
 * A method that this Builder does not have shows a version gap, not an error.
 * An extension has its own release schedule. It loses only that surface. The
 * warning tells that Builder is older than the extension.
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
