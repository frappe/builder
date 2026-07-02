import DOMPurify from "dompurify";
import { marked } from "marked";

marked.use({ breaks: true, gfm: true });

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
