let lastTimestamp = 0;

export function historyTimestamp() {
	// Edits and history replays can happen within the same millisecond.
	lastTimestamp = Math.max(Date.now(), lastTimestamp + 1);
	return lastTimestamp;
}
