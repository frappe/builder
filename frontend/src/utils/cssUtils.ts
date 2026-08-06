// CSS value parsing / normalization helpers (px, spacing shorthand, background).
// Extracted from helpers.ts; re-exported there for backwards compatibility.

import Block from "@/block";

const numericValuePattern = /^(-?(?:\d+(?:\.\d*)?|\.\d+))([a-z%]*)$/i;

function getNumberFromPx(px: string | number | null | undefined): number {
	if (!px) {
		return 0;
	}
	if (typeof px === "number") {
		return px;
	}
	const number = Number(px.replace("px", ""));
	if (isNaN(number)) {
		return 0;
	}
	return number;
}

function addPxToNumber(number: number, round: boolean = true): string {
	number = round ? Math.round(number) : number;
	return `${number}px`;
}

interface BackgroundValue {
	image?: string;
	position?: string;
	size?: string;
	repeat?: string;
	attachment?: string;
	origin?: string;
	clip?: string;
	color?: string;
}

// Based on WebKit and Gecko parsing implementations
function parseBackground(cssText: string): BackgroundValue {
	if (!cssText || typeof cssText !== "string") {
		return {};
	}

	// Tokenize the input preserving quoted strings and functions
	function tokenize(input: string): string[] {
		const tokens: string[] = [];
		let current = "";
		let parenDepth = 0;
		let inQuote: string | null = null;

		for (let i = 0; i < input.length; i++) {
			const char = input[i];

			if (inQuote) {
				current += char;
				if (char === inQuote && input[i - 1] !== "\\") {
					inQuote = null;
				}
				continue;
			}

			if (char === '"' || char === "'") {
				current += char;
				inQuote = char;
				continue;
			}

			if (char === "(") {
				parenDepth++;
				current += char;
				continue;
			}

			if (char === ")") {
				parenDepth--;
				current += char;
				continue;
			}

			if (parenDepth > 0) {
				current += char;
				continue;
			}

			if (char === " " || char === "\t" || char === "\n") {
				if (current) {
					tokens.push(current);
					current = "";
				}
				continue;
			}

			current += char;
		}

		if (current) {
			tokens.push(current);
		}

		return tokens;
	}

	// Parse color value
	function isColor(value: string): boolean {
		return (
			/^(#|rgb|hsl|[a-z]+$)/.test(value) &&
			!["center", "top", "bottom", "left", "right", "fixed", "local", "scroll", "contain", "repeat"].includes(
				value,
			)
		);
	}

	// Parse position values
	function isPosition(value: string): boolean {
		return /^(center|top|bottom|left|right|[-\d.]+(%|px|em|rem|vh|vw)?)$/.test(value);
	}

	// Parse size values
	function isSize(value: string): boolean {
		return /^(cover|contain|auto|[-\d.]+(%|px|em|rem|vh|vw)?)$/.test(value);
	}

	const result: BackgroundValue = {};
	const tokens = tokenize(cssText.trim());
	let i = 0;

	while (i < tokens.length) {
		const token = tokens[i];

		// Handle url() and gradients
		if (token.startsWith("url(") || token.includes("gradient")) {
			result.image = token;
			i++;
			continue;
		}

		// Handle color
		if (isColor(token)) {
			result.color = token;
			i++;
			continue;
		}

		// Handle position and size
		if (isPosition(token)) {
			let position = [token];

			// Check for second position value
			if (i + 1 < tokens.length && isPosition(tokens[i + 1])) {
				position.push(tokens[i + 1]);
				i++;
			}

			result.position = position.join(" ");

			// Check for size after '/'
			if (i + 2 < tokens.length && tokens[i + 1] === "/" && isSize(tokens[i + 2])) {
				let size = [tokens[i + 2]];
				if (i + 3 < tokens.length && isSize(tokens[i + 3])) {
					size.push(tokens[i + 3]);
					i++;
				}
				result.size = size.join(" ");
				i += 2;
			}

			i++;
			continue;
		}

		// Handle repeat
		if (/^(no-repeat|repeat(-[xy])?|round|space)$/.test(token)) {
			result.repeat = token;
			i++;
			continue;
		}

		// Handle attachment
		if (/^(fixed|local|scroll)$/.test(token)) {
			result.attachment = token;
			i++;
			continue;
		}

		// Handle origin/clip
		if (/^(border|padding|content)-box$/.test(token)) {
			if (!result.origin) {
				result.origin = token;
			} else {
				result.clip = token;
			}
			i++;
			continue;
		}

		i++;
	}

	return result;
}

const parseAndSetBackground = (styles: BlockStyleMap) => {
	if (styles.background) {
		const { color, image, position, size, repeat } = parseBackground(styles.background as string);
		delete styles.background;
		if (color) styles.backgroundColor = color;
		if (image) styles.backgroundImage = image;
		if (position) styles.backgroundPosition = position;
		if (size) styles.backgroundSize = size;
		if (repeat) styles.backgroundRepeat = repeat;
	}
};

function shortenNumber(num: number): string {
	if (num < 1000) return num.toString();
	const units = ["", "k", "M", "B", "T"];
	const order = Math.floor(Math.log10(num) / 3);
	const unitname = units[order];
	const shortNum = num / Math.pow(1000, order);
	return shortNum % 1 === 0 ? shortNum.toFixed(0) + unitname : shortNum.toFixed(1) + unitname;
}

// Every spacing property is a shorthand backed by longhands that override it per slot.
// The slots differ (4 box sides vs 2 gap axes) and so do the longhand names, but the
// read/write logic is identical, so each type just declares its shape here.
export type SpacingType = "margin" | "padding" | "gap";

const SPACING_PROPERTIES: Record<SpacingType, { longhands: styleProperty[]; slots: ShorthandSlots }> = {
	margin: { longhands: ["marginTop", "marginRight", "marginBottom", "marginLeft"], slots: 4 },
	padding: { longhands: ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"], slots: 4 },
	gap: { longhands: ["rowGap", "columnGap"], slots: 2 },
};

function setSpacing(block: Block, type: SpacingType, value: string) {
	const { longhands } = SPACING_PROPERTIES[type];
	const props: styleProperty[] = [type, ...longhands];
	props.forEach((prop) => block.setStyle(prop, null));
	const shorthand = value.trim();
	if (shorthand) block.setStyle(type, shorthand);
}

function getSpacing(
	block: Block,
	type: SpacingType,
	opts?: { nativeOnly?: boolean; cascading?: boolean },
): string {
	const { longhands, slots } = SPACING_PROPERTIES[type];
	const nativeOnly = opts?.nativeOnly ?? false;
	const cascading = opts?.cascading ?? false;
	const baseValue = block.getStyle(type, undefined, nativeOnly, cascading);
	const base = String(baseValue ?? (nativeOnly && !cascading ? "" : "unset"));
	const baseParts = expandShorthand(base, slots);
	const values = longhands.map((prop, index) =>
		String(block.getStyle(prop, undefined, nativeOnly, cascading) ?? baseParts[index]),
	);
	if (values.every((value, index) => value === baseParts[index])) {
		return base;
	}
	// A slot left unset while others are set falls back to an empty base; treat it as 0
	// so the reconstructed shorthand stays well-formed and expands back to the same slots.
	return collapseShorthand(
		values.map((value) => value || "0px"),
		slots,
	);
}

/**
 * Extracts the numeric value and unit from a CSS value string
 * @param value - CSS value string (e.g., "10px", "1.5em", "20")
 * @returns Object containing the number and unit parts
 */
function extractNumberAndUnit(value: string): { number: string; unit: string } {
	const match = value.match(/([0-9.]+)([a-z%]*)/) || ["", "0", ""];
	return { number: match[1], unit: match[2] };
}

/**
 * Adds a unit to a number if it doesn't already have one
 * @param numberStr - String containing a number with or without a unit
 * @param unit - Default unit to add if none exists
 * @returns String with unit attached
 */
function addUnitToNumber(numberStr: string, unit: string): string {
	const match = numberStr.match(numericValuePattern);
	if (match) {
		const [, number, existingUnit] = match;
		return existingUnit ? numberStr : number + unit;
	}
	return numberStr;
}

/**
 * Removes the default unit from numeric values for display in controls.
 * Other units remain visible.
 */
function removeDefaultUnit(value: string, defaultUnit: string): string {
	return value
		.split(/(\s+)/)
		.map((part) => {
			const match = part.match(numericValuePattern);
			return match?.[2].toLowerCase() === defaultUnit.toLowerCase() ? match[1] : part;
		})
		.join("");
}

// Splits on whitespace outside parentheses, so `calc(10px + 5%)` stays one part.
function splitCssValueList(value: string): string[] {
	const parts: string[] = [];
	let current = "";
	let depth = 0;
	for (const char of value) {
		if (char === "(") depth++;
		if (char === ")") depth--;
		if (/\s/.test(char) && depth === 0) {
			if (current) parts.push(current);
			current = "";
		} else {
			current += char;
		}
	}
	if (current) parts.push(current);
	return parts;
}

// 2 slots for gap (row, column), 4 for the box sides (top, right, bottom, left).
type ShorthandSlots = 2 | 4;

// `a` → every slot, `a b` → [a,b,a,b], `a b c` → [a,b,c,b].
function expandShorthand(value: unknown, slots: ShorthandSlots): string[] {
	const parts = splitCssValueList(String(value ?? "").trim()).filter(
		(part: string) => part !== "" && part !== "Mixed" && part !== "unset",
	);
	if (!parts.length) return Array(slots).fill("");
	if (parts.length >= slots) return parts.slice(0, slots);
	if (parts.length === 1) return Array(slots).fill(parts[0]);
	return [parts[0], parts[1], parts[2] ?? parts[0], parts[1]];
}

// Inverse of expandShorthand: drops every trailing value that CSS can infer.
function collapseShorthand(parts: unknown[], slots: ShorthandSlots): string {
	const values = Array.from({ length: slots }, (_, index) => String(parts[index] ?? ""));
	while (values.length > 2 && values[values.length - 1] === values[values.length - 3]) values.pop();
	if (values.length === 2 && values[0] === values[1]) values.pop();
	return values.join(" ");
}

function expandBoxShorthand(value: unknown): string[] {
	return expandShorthand(value, 4);
}

function collapseBoxShorthand(parts: unknown[]): string {
	return collapseShorthand(parts, 4);
}

function expandGapShorthand(value: unknown): [string, string] {
	return expandShorthand(value, 2) as [string, string];
}

function collapseGapShorthand(parts: unknown[]): string {
	// An unset axis has to become 0px, otherwise the pair reads as a single value.
	const axes = parts.map((part) => {
		const value = String(part ?? "").trim();
		if (value !== "" && value !== "Mixed" && value !== "unset") {
			return value;
		} else {
			return "0px";
		}
	});
	return collapseShorthand(axes, 2);
}

/**
 * Normalizes CSS values by adding the default unit where missing.
 * Handles both single and whitespace-separated numeric values.
 * @param value - CSS value string
 * @param defaultUnit - Unit to add to unitless numbers
 * @returns Normalized value string with units added
 */
function normalizeValueWithUnits(value: string, defaultUnit: string): string {
	if (!defaultUnit) return value;
	return value
		.split(/(\s+)/)
		.map((part) => addUnitToNumber(part, defaultUnit))
		.join("");
}

export {
	addPxToNumber,
	collapseBoxShorthand,
	collapseGapShorthand,
	expandBoxShorthand,
	expandGapShorthand,
	extractNumberAndUnit,
	getNumberFromPx,
	getSpacing,
	normalizeValueWithUnits,
	parseAndSetBackground,
	removeDefaultUnit,
	setSpacing,
	shortenNumber,
};
