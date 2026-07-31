const MAX_OPTIONS = 20;

// typing filters to matching options; an exact match (the current selection)
// shows the list windowed around it, with about a third of the window above it
function filterOptions<Option extends { label: string }>(
	options: Option[],
	query: string,
	limit = MAX_OPTIONS,
): Option[] {
	const normalizedQuery = query.trim().toLowerCase();
	if (!normalizedQuery) return options.slice(0, limit);

	const selectedIndex = options.findIndex((option) => option.label.toLowerCase() === normalizedQuery);
	if (selectedIndex === -1) {
		return options.filter((option) => option.label.toLowerCase().includes(normalizedQuery)).slice(0, limit);
	}

	const maxStart = Math.max(options.length - limit, 0);
	const start = Math.min(Math.max(selectedIndex - Math.floor(limit / 3), 0), maxStart);
	return options.slice(start, start + limit);
}

export { filterOptions, MAX_OPTIONS };
