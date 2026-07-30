const MAX_OPTIONS = 20;
// options kept above the selected option when the list is windowed around it
const NEIGHBOURS_ABOVE = 3;

// typing filters to matching options; an exact match (the current selection)
// shows the list windowed around it instead, so its neighbours stay visible
function filterOptions<Option extends { label: string }>(
	options: Option[],
	query: string,
	limit = MAX_OPTIONS,
): Option[] {
	const normalizedQuery = query.trim().toLowerCase();
	if (!normalizedQuery) return options.slice(0, limit);

	const selectedIndex = options.findIndex((option) => option.label.toLowerCase() === normalizedQuery);
	if (selectedIndex !== -1) return windowAround(options, selectedIndex, limit);

	return options.filter((option) => option.label.toLowerCase().includes(normalizedQuery)).slice(0, limit);
}

function windowAround<Option>(options: Option[], index: number, limit: number): Option[] {
	const maxStart = Math.max(options.length - limit, 0);
	const start = Math.min(Math.max(index - NEIGHBOURS_ABOVE, 0), maxStart);
	return options.slice(start, start + limit);
}

export { filterOptions, MAX_OPTIONS };
