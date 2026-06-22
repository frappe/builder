// Light syntax highlight for redirect rules, matching what the framework's
// path_resolver actually treats as special:
// - "source" (From) is a regular expression  -> highlight its metacharacters
// - "target" (To) is a replacement string    -> only \1, \2 … backreferences matter
const escapeHtml = (value: string) =>
	value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

export function highlightSource(value: string): string {
	return escapeHtml(value).replace(
		/[()[\].*+?^$|]/g,
		(m) => `<span class="text-ink-amber-6">${m}</span>`,
	);
}

export function highlightTarget(value: string): string {
	return escapeHtml(value).replace(/\\\d+/g, (m) => `<span class="text-ink-blue-8">${m}</span>`);
}
