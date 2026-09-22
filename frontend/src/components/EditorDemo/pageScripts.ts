import type { EditorDemoPayload } from "@/utils/editorDemo";

/**
 * Run the page's client scripts the way the published page does. They are the site's own,
 * already unrestricted on the live page, and they find the canvas copy of the page in the
 * document. Only their CSS needs fencing in, so it cannot restyle the editor.
 */
export function runPageScripts(scripts: EditorDemoPayload["scripts"]) {
	for (const { script_type, script } of scripts) {
		const isCSS = script_type === "CSS";
		const element = document.createElement(isCSS ? "style" : "script");
		element.textContent = isCSS ? `@scope (.canvas-container .canvas) {\n${script}\n}` : script;
		document.head.append(element);
	}
	// they wait for these, which fired long before the canvas had the page
	document.dispatchEvent(new Event("DOMContentLoaded", { bubbles: true }));
	window.dispatchEvent(new Event("load"));
}
