/**
 * Runs page client scripts inside one breakpoint shadow root.
 *
 * A published page loads each attached script as a <script src> or a stylesheet
 * link, in attachment order. This reproduces that in the canvas. CSS goes into
 * the shadow root as one style element. JavaScript runs against the canvas
 * facades. Re-applying replaces both, so an edit re-runs the scripts.
 */
import type { BuilderClientScript } from "@/types/doctypes";
import { CanvasScriptScope } from "@/utils/canvasScriptFacade";

const WIDTH_ONLY_CONDITION = /^\(\s*(?:min|max)-width\s*:[^()]+\)(?:\s+and\s+\(\s*(?:min|max)-width\s*:[^()]+\))*$/i;

/**
 * A shadow root resolves @media against the editor viewport, so every
 * breakpoint would get the same answer. The canvas host is a size container,
 * so width-only queries convert to container queries and resolve per
 * breakpoint. Anything else (print, orientation, hover) passes through.
 */
function toContainerQueries(css: string) {
	try {
		const sheet = new CSSStyleSheet();
		sheet.replaceSync(css);
		return Array.from(sheet.cssRules, rewriteMediaRule).join("\n");
	} catch {
		return css;
	}
}

function rewriteMediaRule(rule: CSSRule) {
	if (!(rule instanceof CSSMediaRule)) return rule.cssText;
	const condition = rule.conditionText.trim();
	if (!WIDTH_ONLY_CONDITION.test(condition)) return rule.cssText;
	const body = Array.from(rule.cssRules, (nested) => nested.cssText).join("\n");
	return `@container ${condition} {\n${body}\n}`;
}

function isJavaScript(script: BuilderClientScript) {
	return script.script_type === "JavaScript";
}

class PageScriptRuntime {
	private styleElement = document.createElement("style");
	private scope: CanvasScriptScope | null = null;

	constructor(
		private root: ShadowRoot,
		private breakpointWidth: number,
	) {
		this.root.appendChild(this.styleElement);
	}

	/** Apply the CSS and run the JavaScript together. Neither applies when stopped. */
	apply(scripts: BuilderClientScript[], runScripts: boolean, pageData: Record<string, any> = {}) {
		this.stop();
		if (!runScripts) {
			this.styleElement.textContent = "";
			this.setSizeContainer(false);
			return;
		}
		this.applyStyles(scripts);
		this.scope = new CanvasScriptScope(this.root, this.breakpointWidth, pageData);
		scripts.filter(isJavaScript).forEach((script) => this.runScript(script));
	}

	/** Undo listeners and timers only. BuilderCanvas.vue remounts the block tree separately to undo any DOM change. */
	stop() {
		this.scope?.dispose();
		this.scope = null;
	}

	destroy() {
		this.stop();
		this.styleElement.remove();
	}

	private applyStyles(scripts: BuilderClientScript[]) {
		const css = scripts
			.filter((script) => script.script_type === "CSS")
			.map((script) => toContainerQueries(script.script ?? ""))
			.join("\n");
		this.styleElement.textContent = css;
		this.setSizeContainer(css.includes("@container"));
	}

	/**
	 * container-type also applies layout containment, which makes the host a
	 * containing block for absolutely positioned blocks. Only pay that cost on
	 * pages whose CSS has width media queries to resolve.
	 */
	private setSizeContainer(needed: boolean) {
		(this.root.host as HTMLElement).style.containerType = needed ? "inline-size" : "";
	}

	private runScript(script: BuilderClientScript) {
		if (!script.script?.trim() || !this.scope) return;
		try {
			// parameters shadow the real globals, the way a published page sees them
			const run = new Function("document", "window", "self", "globalThis", script.script);
			run(this.scope.document, this.scope.window, this.scope.window, this.scope.window);
		} catch (error) {
			console.error(`Error in page client script "${script.name}":`, error);
		}
	}
}

export { PageScriptRuntime };
