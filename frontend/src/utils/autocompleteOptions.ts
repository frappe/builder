const MAX_OPTIONS = 20;

// keeps every match for the query in the list, then fills the rest of the list with the
// remaining options so the dropdown always offers something to browse
function filterOptions<Option extends { label: string }>(
	options: Option[],
	query: string,
	limit = MAX_OPTIONS,
): Option[] {
	const normalizedQuery = query.trim().toLowerCase();
	if (!normalizedQuery) return options.slice(0, limit);

	const matched: Option[] = [];
	const rest: Option[] = [];
	options.forEach((option) => {
		if (option.label.toLowerCase().includes(normalizedQuery)) {
			matched.push(option);
		} else {
			rest.push(option);
		}
	});

	return [...matched, ...rest].slice(0, limit);
}

export { filterOptions, MAX_OPTIONS };
