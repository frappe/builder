export type ContextUsage = { used: number; total: number; pct: number };

/** How full the model's window was at the end of a turn: the last call's prompt
 * carries the whole conversation so far. */
export function contextUsageOf(debug?: Record<string, any> | null): ContextUsage | null {
	const used = debug?.tokens?.per_call?.at(-1)?.prompt || 0;
	const total = debug?.contextWindow || 0;
	if (!used || !total) return null;
	return { used, total, pct: Math.round((used / total) * 100) };
}
