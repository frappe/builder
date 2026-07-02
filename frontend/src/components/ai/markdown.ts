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

/** Markdown → sanitized HTML for AI chat messages (editor panel + dashboard chat). */
export function renderMarkdown(content: string): string {
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
		],
		ALLOWED_ATTR: ["href", "target", "rel", "class"],
		ADD_ATTR: ["target"],
	});
}
