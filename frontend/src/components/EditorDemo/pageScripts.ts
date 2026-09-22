import type { EditorDemoPayload } from "@/utils/editorDemo";

// a page's CSS roots, which on the canvas mean the canvas copy of the page
const DOCUMENT_ROOTS = /(^|[{},]\s*)(?:html|body|:root)(?=[\s{,.:#[>+~])/g;

/**
 * Run the page's client scripts the way the published page does. They are the site's own,
 * already unrestricted on the live page, and they find the canvas copy of the page in the
 * document. Their CSS is fenced into the canvas, and while they start up, document.body is
 * the page. Later handlers see the editor's body, which the editor's own popovers need.
 */
export function runPageScripts(scripts: EditorDemoPayload["scripts"], page: HTMLElement) {
	Object.defineProperty(document, "body", { get: () => page, configurable: true });
	for (const { script_type, script } of scripts) {
		const isCSS = script_type === "CSS";
		const element = document.createElement(isCSS ? "style" : "script");
		element.textContent = isCSS
			? `@scope (.canvas-container .canvas) {\n${script.replace(DOCUMENT_ROOTS, "$1:scope")}\n}`
			: script;
		document.head.append(element);
	}
	// they wait for these, which fired long before the canvas had the page
	document.dispatchEvent(new Event("DOMContentLoaded", { bubbles: true }));
	window.dispatchEvent(new Event("load"));
	Reflect.deleteProperty(document, "body");
}
