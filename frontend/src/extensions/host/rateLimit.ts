/**
 * A message budget per extension.
 *
 * An extension in a loop can flood `postMessage` and freeze the editor. A call
 * over budget is refused, never queued, so the work per message drops to a
 * lookup and the extension recovers when the window rolls over.
 */

/** A startup burst is a handful of calls. A loop is thousands, so the two do not overlap. */
const MESSAGES_PER_WINDOW = 100;
const WINDOW_MS = 1000;

export const createBudget = (extension: string, perWindow = MESSAGES_PER_WINDOW) => {
	let windowStart = 0;
	let used = 0;

	// the window owns the warning, because it owns the boundary that makes "once" mean anything
	const take = () => {
		const now = Date.now();
		if (now - windowStart >= WINDOW_MS) {
			windowStart = now;
			used = 0;
		}

		used += 1;
		if (used <= perWindow) return true;
		if (used === perWindow + 1) console.warn(`Extension "${extension}" is over its message budget.`);
		return false;
	};

	return { take };
};

export type Budget = ReturnType<typeof createBudget>;
