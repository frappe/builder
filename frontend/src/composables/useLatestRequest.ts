const requestSeqByKey = new Map<string, number>();

export type LatestRequestResult<T> = { stale: true } | { stale: false; value: T };

export function useLatestRequest() {
	function guard(key: string): () => boolean {
		const seq = (requestSeqByKey.get(key) ?? 0) + 1;
		requestSeqByKey.set(key, seq);
		return () => requestSeqByKey.get(key) === seq;
	}

	function invalidate(key: string): void {
		requestSeqByKey.set(key, (requestSeqByKey.get(key) ?? 0) + 1);
	}

	async function run<T>(
		key: string,
		fn: () => T | Promise<T>,
	): Promise<LatestRequestResult<T>> {
		const isLatest = guard(key);
		const value = await fn();
		return isLatest() ? { stale: false, value } : { stale: true };
	}

	return { guard, invalidate, run };
}
