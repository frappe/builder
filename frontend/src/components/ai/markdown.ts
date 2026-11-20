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

// A web address in plain text, without the punctuation that usually ends the sentence it's in.
const WEB_ADDRESS = /\b(?:https?:\/\/|www\.)[^\s<>"']*[^\s<>"'.,;:!?)\]}]/g;

/** A user's plain-text message as runs of text and the web addresses in it, so the
 * addresses render as links without the message going through markdown. */
export function linkParts(text: string): { text: string; href?: string }[] {
	const parts: { text: string; href?: string }[] = [];
	let last = 0;
	for (const match of text.matchAll(WEB_ADDRESS)) {
		const start = match.index ?? 0;
		if (start > last) parts.push({ text: text.slice(last, start) });
		const href = match[0].startsWith("www.") ? `https://${match[0]}` : match[0];
		parts.push({ text: match[0], href });
		last = start + match[0].length;
	}
	if (last < text.length) parts.push({ text: text.slice(last) });
	return parts;
}

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
