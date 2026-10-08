/**
 * A message budget for each extension.
 *
 * An extension in a loop can send too many messages and stop the editor. The
 * budget refuses a call over the limit. It does not queue the call. So each
 * extra message costs only one check. The extension can send again in the
 * next window.
 */

/** Startup sends a few calls. A loop sends thousands. So this limit does not stop startup. */
const MESSAGES_PER_WINDOW = 100;
const WINDOW_MS = 1000;

export const createBudget = (extension: string, perWindow = MESSAGES_PER_WINDOW) => {
	let windowStart = 0;
	let used = 0;

	// the window controls the warning. So the warning shows one time in each window
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
