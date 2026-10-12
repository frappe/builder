import DOMPurify from "dompurify";
import { marked } from "marked";

marked.use({ breaks: true, gfm: true });

// Chat links open in a new tab — a same-tab navigation would blow away the SPA
// (and the conversation the user is in the middle of).
DOMPurify.addHook("afterSanitizeAttributes", (node) => {
	if (node.tagName === "A") {
		node.setAttribute("target", "_blank");
		node.setAttribute("rel", "noopener noreferrer");
	}
});

// A streamed token re-renders the whole transcript, so every finished message would
// otherwise be parsed and sanitized again per token. Least recently read goes first,
// which ages out a stream's partial snapshots and keeps what's on screen.
const MAX_CACHED = 300;
const rendered = new Map<string, string>();

/** Markdown → sanitized HTML for AI chat messages (editor panel + dashboard chat). */
export function renderMarkdown(content: string): string {
	const html = rendered.get(content) ?? sanitize(content);
	rendered.delete(content);
	rendered.set(content, html);
	if (rendered.size > MAX_CACHED) {
		const oldest = rendered.keys().next();
		if (!oldest.done) rendered.delete(oldest.value);
	}
	return html;
}

function sanitize(content: string): string {
	return DOMPurify.sanitize(marked.parse(content) as string, {
		ALLOWED_TAGS: [
			"p",
			"br",
			"strong",
			"em",
			"code",
			"pre",
			"ul",
			"ol",
			"li",
			"a",
			"h1",
			"h2",
			"h3",
			"h4",
			"blockquote",
			"hr",
			"span",
			"table",
			"thead",
			"tbody",
			"tr",
			"th",
			"td",
		],
		ALLOWED_ATTR: ["href", "target", "rel", "class", "align"],
		ADD_ATTR: ["target"],
	});
}
