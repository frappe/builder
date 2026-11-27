const STYLE_TAG = /<style[\s>]/i;
const IMPORT_RULE = /@import\s[^;]+;/g;
const DOCUMENT_ROOT = /(^|[\s>+~,(])(?::root|html|body)(?![\w-])/g;
// Serializing the rules writes an escaped "<" ("\3c ") as a bare "<" in strings and as "\<" in names. Raw in <style>,
// "</style" would end the element, and a sanitizer drops a <style> whose text looks like markup, so each such "<" is
// escaped again (an odd run of backslashes before it ends in the one escaping it). A media range's "<" is followed
// by a space or "=", and stays.
const MARKUP_START = /(\\*)<(?=[/\w!])/g;
const escapeMarkup = (_: string, slashes: string) => (slashes.length % 2 ? slashes.slice(1) : slashes) + "\\3c ";

export function scopeStyles(html: string, scope: string) {
	if (!STYLE_TAG.test(html)) return html;
	const template = document.createElement("template");
	template.innerHTML = html;
	for (const style of template.content.querySelectorAll("style")) {
		style.textContent = scopeCSS(style.textContent || "", scope);
	}
	return template.innerHTML;
}

function scopeCSS(css: string, scope: string) {
	const sheet = new CSSStyleSheet();
	sheet.replaceSync(css.replace(IMPORT_RULE, ""));
	scopeDocumentRoot(sheet.cssRules);
	const rules = [...sheet.cssRules];
	// @scope only holds style and grouping rules; @font-face, @keyframes and the like stay global
	const global = rules.filter((rule) => !isScopable(rule)).map((rule) => rule.cssText);
	const scoped = rules.filter(isScopable).map((rule) => rule.cssText);
	const imports = css.match(IMPORT_RULE) || [];
	const text = [...imports, ...global, `@scope (${scope}) {`, ...scoped, "}"].join("\n");
	return text.replace(MARKUP_START, escapeMarkup);
}

function scopeDocumentRoot(rules: CSSRuleList) {
	for (const rule of rules) {
		if (rule instanceof CSSStyleRule) {
			rule.selectorText = rule.selectorText.replace(DOCUMENT_ROOT, "$1:scope");
		} else if (rule instanceof CSSGroupingRule) {
			scopeDocumentRoot(rule.cssRules);
		}
	}
}

function isScopable(rule: CSSRule) {
	return rule instanceof CSSStyleRule || rule instanceof CSSGroupingRule;
}
