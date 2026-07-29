const MAX_OPTIONS = 20;
const DEFAULT_RADIUS = { upper: 10, lower: 9 };

type WindowRadius = {
	upper?: number;
	lower?: number;
};

type FilterOptionsConfig = {
	limit?: number;
	windowRadius?: WindowRadius;
};

// matches first, then the rest. pass windowRadius to keep each match in place and
// show the options around it instead.
function filterOptions<Option extends { label: string }>(
	options: Option[],
	query: string,
	{ limit = MAX_OPTIONS, windowRadius }: FilterOptionsConfig = {},
): Option[] {
	const normalizedQuery = query.trim().toLowerCase();
	if (!normalizedQuery) return options.slice(0, limit);

	const matchIndexes: number[] = [];
	const matched: Option[] = [];
	const rest: Option[] = [];
	options.forEach((option, index) => {
		if (option.label.toLowerCase().includes(normalizedQuery)) {
			matchIndexes.push(index);
			matched.push(option);
		} else {
			rest.push(option);
		}
	});
	if (!matchIndexes.length) return options.slice(0, limit);
	if (!windowRadius) return [...matched, ...rest].slice(0, limit);

	const kept = new Set<number>();
	const radius = { ...DEFAULT_RADIUS, ...windowRadius };
	matchIndexes.forEach((matchIndex) => {
		const start = Math.max(0, matchIndex - radius.upper);
		const end = Math.min(options.length - 1, matchIndex + radius.lower);
		for (let index = start; index <= end; index++) {
			kept.add(index);
		}
	});
	return options.filter((_, index) => kept.has(index)).slice(0, limit);
}

export { filterOptions, MAX_OPTIONS };
