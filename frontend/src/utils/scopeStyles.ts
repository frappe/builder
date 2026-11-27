const STYLE_TAG = /<style[\s>]/i;
const IMPORT_RULE = /@import\s[^;]+;/g;
const DOCUMENT_ROOT = /(^|[\s>+~,(])(?::root|html|body)(?![\w-])/g;

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
	return [...imports, ...global, `@scope (${scope}) {`, ...scoped, "}"].join("\n");
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
