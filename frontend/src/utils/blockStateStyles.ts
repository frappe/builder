/**
 * Turns a block's state styles (hover:, focus:, active:) into canvas CSS.
 *
 * A published page puts every style in a stylesheet, so `.fb-x:hover` wins on
 * specificity alone. The canvas renders a block's regular styles inline, and an
 * inline declaration beats any rule, so each state declaration needs !important
 * to apply while the state holds. Mirrors append_state_style in builder_page.py.
 */
import { splitStylePrefix, toKebabCase } from "@/utils/helpers";

type BlockStateStyleRegistrar = (uid: string, breakpoint: string, css: string) => () => void;

function escapeAttributeValue(value: string) {
	return value.replaceAll("\\", "\\\\").replaceAll('"', '\\"');
}

/** Matches one block inside one breakpoint's canvas. */
function blockSelector(uid: string, breakpoint: string) {
	const block = escapeAttributeValue(uid);
	const device = escapeAttributeValue(breakpoint);
	return `[data-block-uid="${block}"][data-breakpoint="${device}"]`;
}

function toDeclaration(property: string, value: StyleValue) {
	const text = property === "fontFamily" ? String(value).replace(/ /g, "\\ ") : String(value);
	const priority = text.includes("!important") ? "" : " !important";
	return `${toKebabCase(property)}: ${text}${priority};`;
}

function isRenderable(property: string, value: StyleValue) {
	return !property.startsWith("__") && value !== null && value !== undefined && value !== "";
}

/** One rule per state, so `hover:color` and `hover:background` share a block. */
function toStateStyleRules(styles: BlockStyleMap, selector: string) {
	const declarationsByState = new Map<string, string[]>();
	Object.entries(styles).forEach(([style, value]) => {
		const { prefix, property } = splitStylePrefix(style);
		if (!prefix || !isRenderable(property, value)) return;
		const state = prefix.slice(0, -1);
		declarationsByState.set(state, [
			...(declarationsByState.get(state) ?? []),
			toDeclaration(property, value),
		]);
	});
	return Array.from(
		declarationsByState,
		([state, declarations]) => `${selector}:${state} { ${declarations.join(" ")} }`,
	).join("\n");
}

export { blockSelector, toStateStyleRules };
export type { BlockStateStyleRegistrar };
