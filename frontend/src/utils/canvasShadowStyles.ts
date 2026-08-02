/**
 * Shares the editor's stylesheets with every canvas shadow root.
 *
 * A shadow root does not inherit document styles, so the block tree renders
 * unstyled without this. Each document <style>/<link> becomes one constructable
 * CSSStyleSheet, adopted by every shadow root by reference: parsed once and
 * shared, instead of cloned and reparsed per breakpoint. Mutating a sheet in
 * place (replaceSync) updates every root that adopted it, so only a stylesheet
 * entering or leaving the document needs adoptedStyleSheets reassigned.
 *
 * Fonts need no copy. `@font-face` is document scoped and already applies
 * inside every shadow tree. A cross-origin font <link> (Google Fonts) has no
 * readable cssRules, so its sheet ends up empty — harmless, since the font
 * still applies without it.
 */

const STYLE_SOURCE_SELECTOR = 'style, link[rel="stylesheet"]';

const roots = new Set<ShadowRoot>();
const sheetsBySource = new Map<Element, CSSStyleSheet>();
const unwatchBySource = new Map<Element, () => void>();
let headObserver: MutationObserver | null = null;

function cssTextOf(source: Element): string {
	if (source instanceof HTMLStyleElement) return source.textContent ?? "";
	const sheet = (source as HTMLLinkElement).sheet;
	if (!sheet) return "";
	try {
		return Array.from(sheet.cssRules, (rule) => rule.cssText).join("\n");
	} catch {
		return "";
	}
}

function syncSheet(source: Element) {
	const sheet = sheetsBySource.get(source) ?? new CSSStyleSheet();
	try {
		sheet.replaceSync(cssTextOf(source));
	} catch {
		return;
	}
	sheetsBySource.set(source, sheet);
}

/** Hot reload swaps a style tag's text in place, and a link has no rules until it loads. */
function addSource(source: Element) {
	syncSheet(source);
	const resync = () => syncSheet(source);
	const observer = new MutationObserver(resync);
	observer.observe(source, { childList: true, characterData: true, subtree: true });
	source.addEventListener("load", resync);
	unwatchBySource.set(source, () => {
		observer.disconnect();
		source.removeEventListener("load", resync);
	});
}

function removeSource(source: Element) {
	unwatchBySource.get(source)?.();
	unwatchBySource.delete(source);
	sheetsBySource.delete(source);
}

function currentSources() {
	return Array.from(document.querySelectorAll<Element>(STYLE_SOURCE_SELECTOR));
}

function scanDocument() {
	const sources = currentSources();
	const present = new Set(sources);
	Array.from(sheetsBySource.keys())
		.filter((source) => !present.has(source))
		.forEach(removeSource);
	sources.filter((source) => !sheetsBySource.has(source)).forEach(addSource);

	const sheets = sources
		.map((source) => sheetsBySource.get(source))
		.filter((sheet): sheet is CSSStyleSheet => Boolean(sheet));
	roots.forEach((root) => (root.adoptedStyleSheets = sheets));
}

/** Nothing to follow once the editor leaves the canvas, so drop it all together. */
function stopWatching() {
	headObserver?.disconnect();
	headObserver = null;
	unwatchBySource.forEach((unwatch) => unwatch());
	unwatchBySource.clear();
	sheetsBySource.clear();
}

/** Adopts the shared stylesheets into `root` and keeps it in sync from then on. */
function registerShadowStyles(root: ShadowRoot) {
	if (!headObserver) {
		headObserver = new MutationObserver(scanDocument);
		headObserver.observe(document.head, { childList: true });
	}
	roots.add(root);
	scanDocument();
	return () => {
		roots.delete(root);
		if (!roots.size) stopWatching();
	};
}

export { registerShadowStyles };
