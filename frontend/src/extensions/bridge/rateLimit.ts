/**
 * A message budget for each extension. It stops an extension in a loop.
 * The budget refuses a call over the limit. It does not queue the call.
 */

/** Startup sends a few calls. A loop sends thousands. */
const MESSAGES_PER_WINDOW = 100;
const WINDOW_MS = 1000;

export const createBudget = (extension: string, perWindow = MESSAGES_PER_WINDOW) => {
	let windowStart = 0;
	let used = 0;

	// The warning shows one time in each window.
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
