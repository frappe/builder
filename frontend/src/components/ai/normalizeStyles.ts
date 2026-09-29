import { kebabToCamelCase } from "@/utils/helpers";

/**
 * Deterministically fix the mechanical CSS mistakes the model keeps making, so we
 * stop patching the prompt for each one (see git log: camelCased values, etc.).
 * Applied wherever AI-authored styles enter the canvas — generation YAML
 * (convertYAMLtoBlock) and tool edits (applyBlockUpdate) — so both paths are covered
 * by one pass. Pure: returns a new object, never mutates the input.
 *
 * NOT handled here (structural / taste, left to the prompt): merging one-block-per-token
 * text runs, typography metrics, dark/light section rhythm.
 */

// CSS-in-JS camelCases property NAMES only; the model over-applies it to keyword
// VALUES too (justifyContent: 'spaceBetween'). Map each offender to its real CSS form.
const KEYWORD_VALUE_FIX: Record<string, string> = {
	spaceBetween: "space-between",
	spaceAround: "space-around",
	spaceEvenly: "space-evenly",
	flexStart: "flex-start",
	flexEnd: "flex-end",
	rowReverse: "row-reverse",
	columnReverse: "column-reverse",
	wrapReverse: "wrap-reverse",
	preWrap: "pre-wrap",
	preLine: "pre-line",
	noWrap: "nowrap",
};

// Properties that take a length: a bare number gets 'px'. Whitelist (not blocklist) so
// unitless props — lineHeight, fontWeight, opacity, zIndex, flex* — are never touched.
const LENGTH_PROPS = new Set([
	"padding",
	"paddingTop",
	"paddingRight",
	"paddingBottom",
	"paddingLeft",
	"margin",
	"marginTop",
	"marginRight",
	"marginBottom",
	"marginLeft",
	"top",
	"right",
	"bottom",
	"left",
	"inset",
	"width",
	"height",
	"minWidth",
	"maxWidth",
	"minHeight",
	"maxHeight",
	"fontSize",
	"gap",
	"rowGap",
	"columnGap",
	"borderRadius",
	"borderWidth",
	"letterSpacing",
	"wordSpacing",
	"textIndent",
	"outlineWidth",
	"flexBasis",
]);

const BARE_NUMBER = /^-?\d+(\.\d+)?$/;

// Props where a leading/trailing quote is meaningful CSS (don't strip it). fontFamily is
// handled separately above; everything else (position, display, color, gradients, …) never
// legitimately starts or ends with a quote, so a stray one is a model slip.
// gridTemplateAreas/gridTemplate: each row is a double-quoted string ("hero hero").
const QUOTE_MEANINGFUL = new Set(["content", "quotes", "gridTemplateAreas", "gridTemplate"]);

function normalizeValue(prop: string, value: unknown): unknown {
	if (prop === "fontFamily" && typeof value === "string") {
		const v = value.replace(/['"]/g, "").trim();
		// A font TOKEN handle: return var(--id) clean. Never split on comma first —
		// the model sometimes bakes a fallback INSIDE the parens (var(--id, Inter)),
		// and splitting there truncates the var() and drops its closing ) (invalid
		// CSS → the family silently falls back to serif on the published page).
		const match = v.match(/var\(\s*(--[A-Za-z0-9_-]+)/);
		if (match) return `var(${match[1]})`;
		// Literal family: bare name only — strip any fallback stack.
		return v.split(",")[0].trim();
	}
	if (typeof value === "string") {
		let v = value.trim();
		// Strip stray wrapping/trailing quotes the model leaves in keyword values
		// (position: "absolute'" → absolute), which otherwise produce invalid CSS.
		// Only the outer quotes go; internal ones (url('x'), repeat(3, 1fr)) are kept.
		if (!QUOTE_MEANINGFUL.has(prop))
			v = v
				.replace(/^['"]+/, "")
				.replace(/['"]+$/, "")
				.trim();
		if (KEYWORD_VALUE_FIX[v]) return KEYWORD_VALUE_FIX[v];
		if (LENGTH_PROPS.has(prop) && BARE_NUMBER.test(v) && v !== "0") {
			return `${v}px`;
		}
		return v;
	}
	if (typeof value === "number" && LENGTH_PROPS.has(prop) && value !== 0) {
		return `${value}px`;
	}
	return value;
}

export function normalizeStyles(styles: Record<string, any> | null | undefined): Record<string, any> {
	if (!styles || typeof styles !== "object") return {};
	const out: Record<string, any> = {};
	for (const [rawKey, value] of Object.entries(styles)) {
		if (value === null || value === undefined) continue;
		// Custom properties (--brand) are arbitrary — pass through untouched.
		if (rawKey.startsWith("--")) {
			out[rawKey] = value;
			continue;
		}
		// State-prefixed keys (hover:boxShadow) keep the prefix; only the property
		// after the colon is a CSS name to normalize.
		const colon = rawKey.indexOf(":");
		const prefix = colon === -1 ? "" : rawKey.slice(0, colon + 1);
		let prop = kebabToCamelCase(colon === -1 ? rawKey : rawKey.slice(colon + 1));
		// A gradient belongs in backgroundImage, never the `background` shorthand.
		if (prop === "background" && typeof value === "string" && value.includes("gradient(")) {
			prop = "backgroundImage";
		}
		out[prefix + prop] = normalizeValue(prop, value);
	}
	return out;
}
