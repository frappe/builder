import type { EditorDemoPayload } from "@/utils/editorDemo";

// a page's CSS roots, which on the canvas mean the canvas copy of the page
const DOCUMENT_ROOTS = /(^|[{},]\s*)(?:html|body|:root)(?=[\s{,.:#[>+~])/g;
// names each script, so the console and the handler below can tell whose error it is
const SCRIPT_NAME = "builder-page-script";

/**
 * Run the page's client scripts the way the published page does. They are the site's own,
 * already unrestricted on the live page, and they find the canvas copy of the page in the
 * document. Their CSS is fenced into the canvas, and while they start up, document.body is
 * the page. Later handlers see the editor's body, which the editor's own popovers need.
 */
export function runPageScripts(scripts: EditorDemoPayload["scripts"], page: HTMLElement) {
	// the canvas leaves out blocks the page hides, so a script wired to one of them throws
	// where the published page would not: the page's own code meeting a partial copy of itself
	const report = (event: ErrorEvent) => {
		if (!event.filename?.includes(SCRIPT_NAME)) return;
		event.preventDefault();
		console.warn("Page script did not find what it expects on the canvas:", event.error);
	};
	window.addEventListener("error", report);
	Object.defineProperty(document, "body", { get: () => page, configurable: true });
	scripts.forEach(({ script_type, script }, index) => {
		const isCSS = script_type === "CSS";
		const element = document.createElement(isCSS ? "style" : "script");
		element.textContent = isCSS
			? `@scope (.canvas-container .canvas) {\n${script.replace(DOCUMENT_ROOTS, "$1:scope")}\n}`
			: `${script}\n//# sourceURL=${SCRIPT_NAME}-${index + 1}.js`;
		document.head.append(element);
	});
	// they wait for these, which fired long before the canvas had the page
	document.dispatchEvent(new Event("DOMContentLoaded", { bubbles: true }));
	window.dispatchEvent(new Event("load"));
	Reflect.deleteProperty(document, "body");
	window.removeEventListener("error", report);
}
