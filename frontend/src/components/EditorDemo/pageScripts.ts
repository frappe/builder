import type { EditorDemoPayload } from "@/utils/editorDemo";

type PageScript = EditorDemoPayload["scripts"][number];
type LoadListeners = Array<{ script: string; listener: () => void }>;
type CurrentScript = { script: string };

// page CSS is written for a whole document, so on the canvas it may only reach the page
const CANVAS_SCOPE = ".canvas-container .canvas";
const DOCUMENT_ROOTS = /^(:root|html|body)\b/;
// already fired in the editor, so the page's scripts would wait for them forever
const LOAD_EVENTS = new Set(["DOMContentLoaded", "load", "readystatechange"]);

/**
 * Bring the page to life on the canvas the way the published page runs its client scripts.
 * The proxies scope the scripts to the canvas, they are not a sandbox: these are the site's
 * own scripts, which already run unrestricted on the live page hosting the demo.
 */
export function runPageScripts(scripts: PageScript[], page: HTMLElement) {
	const byType = (type: string) => scripts.filter((script) => script.script_type === type);
	adoptCanvasStyles(byType("CSS").map((script) => script.script));

	const onLoad: LoadListeners = [];
	const current = { script: "" };
	const pageDocument = createPageDocument(page, onLoad, current);
	const pageWindow = createPageWindow(pageDocument, onLoad, current);
	for (const { name, script } of byType("JavaScript")) {
		current.script = name;
		run(name, () => new Function("document", "window", "self", script)(pageDocument, pageWindow, pageWindow));
	}
	onLoad.forEach(({ script, listener }) => run(script, listener));
}

function run(name: string, fn: () => void) {
	try {
		fn();
	} catch (error) {
		console.warn(`Page script "${name}" failed on the demo canvas`, error);
	}
}

function adoptCanvasStyles(styles: string[]) {
	const sheet = new CSSStyleSheet();
	sheet.replaceSync(styles.join("\n"));
	scopeRules(sheet.cssRules);
	document.adoptedStyleSheets = [...document.adoptedStyleSheets, sheet];
}

function scopeRules(rules: CSSRuleList) {
	for (const rule of Array.from(rules)) {
		if (rule instanceof CSSStyleRule) {
			rule.selectorText = splitSelectors(rule.selectorText).map(scopeSelector).join(", ");
		} else if (rule instanceof CSSGroupingRule) {
			scopeRules(rule.cssRules);
		}
	}
}

function scopeSelector(selector: string) {
	return DOCUMENT_ROOTS.test(selector)
		? selector.replace(DOCUMENT_ROOTS, CANVAS_SCOPE)
		: `${CANVAS_SCOPE} ${selector}`;
}

// commas inside :is(), :not() and friends belong to one selector
function splitSelectors(selectorText: string) {
	const selectors = [""];
	let depth = 0;
	for (const char of selectorText) {
		depth += char === "(" ? 1 : char === ")" ? -1 : 0;
		if (char === "," && depth === 0) selectors.push("");
		else selectors[selectors.length - 1] += char;
	}
	return selectors.map((selector) => selector.trim()).filter(Boolean);
}

function listenFor(target: EventTarget, onLoad: LoadListeners, current: CurrentScript) {
	return (type: string, listener: EventListenerOrEventListenerObject, options?: AddEventListenerOptions) => {
		if (!LOAD_EVENTS.has(type)) {
			return target.addEventListener(type, listener, options);
		}
		const event = new Event(type);
		onLoad.push({
			script: current.script,
			listener: () =>
				typeof listener === "function" ? listener.call(target, event) : listener.handleEvent(event),
		});
	};
}

// the page's scripts see the canvas copy of the page as their document
function createPageDocument(page: HTMLElement, onLoad: LoadListeners, current: CurrentScript) {
	const overrides: Record<string | symbol, unknown> = {
		body: page,
		documentElement: page,
		querySelector: (selector: string) => page.querySelector(selector),
		querySelectorAll: (selector: string) => page.querySelectorAll(selector),
		getElementById: (id: string) => page.querySelector(`#${CSS.escape(id)}`),
		getElementsByClassName: (names: string) => page.getElementsByClassName(names),
		getElementsByTagName: (name: string) => page.getElementsByTagName(name),
		addEventListener: listenFor(document, onLoad, current),
	};
	return withOverrides(document, overrides);
}

function createPageWindow(pageDocument: Document, onLoad: LoadListeners, current: CurrentScript) {
	return withOverrides(window, {
		document: pageDocument,
		addEventListener: listenFor(window, onLoad, current),
	});
}

function withOverrides<T extends object>(target: T, overrides: Record<string | symbol, unknown>) {
	return new Proxy(target, {
		get(object, property) {
			if (property in overrides) return overrides[property];
			const value = Reflect.get(object, property, object);
			// native methods need their own receiver; capitalised values are constructors
			const isMethod = typeof value === "function" && !/^[A-Z]/.test(String(property));
			return isMethod ? value.bind(object) : value;
		},
	}) as T;
}
