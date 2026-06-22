// Light syntax highlight for redirect rules. Mirrors what the framework's
// path_resolver supports: "source" is a regex (metacharacters below) and
// "target" can reuse captured groups via \1, \2, … backreferences.
export function highlightRedirectSyntax(value: string): string {
	const escaped = value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
	return escaped
		.replace(/\\\d+/g, (m) => `<span class="text-ink-blue-8">${m}</span>`)
		.replace(/[()[\].*+?^$|]/g, (m) => `<span class="text-ink-amber-6">${m}</span>`);
}
