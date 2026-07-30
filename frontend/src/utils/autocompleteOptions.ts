const MAX_OPTIONS = 20;
// how far down the window a match sits, so more of its neighbours show above it
const MATCH_POSITION = 1 / 3;

function windowAround(matchIndex: number, limit: number, total: number): [number, number] {
	const offset = Math.floor((limit - 1) * MATCH_POSITION);
	const start = Math.min(Math.max(0, matchIndex - offset), Math.max(0, total - limit));
	return [start, Math.min(total - 1, start + limit - 1)];
}

// keeps every match in place and shows the options around it
function filterOptions<Option extends { label: string }>(
	options: Option[],
	query: string,
	limit = MAX_OPTIONS,
): Option[] {
	const normalizedQuery = query.trim().toLowerCase();
	if (!normalizedQuery || options.length <= limit) return options.slice(0, limit);

	const matchIndexes = options.reduce((indexes: number[], option, index) => {
		if (option.label.toLowerCase().includes(normalizedQuery)) indexes.push(index);
		return indexes;
	}, []);
	if (!matchIndexes.length) return options.slice(0, limit);

	const kept = new Set<number>();
	matchIndexes.forEach((matchIndex) => {
		const [start, end] = windowAround(matchIndex, limit, options.length);
		for (let index = start; index <= end; index++) {
			kept.add(index);
		}
	});
	return options.filter((_, index) => kept.has(index)).slice(0, limit);
}

export { filterOptions, MAX_OPTIONS };
