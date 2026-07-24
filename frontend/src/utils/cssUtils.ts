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

function setBoxSpacing(block: Block, type: "padding" | "margin", value: string) {
	const props = [type, `${type}Top`, `${type}Right`, `${type}Bottom`, `${type}Left`];
	props.forEach((prop) => block.setStyle(prop, null));
	const shorthand = value.trim();
	if (shorthand) block.setStyle(type, shorthand);
}

function getBoxSpacing(
	block: Block,
	type: "padding" | "margin",
	opts?: { nativeOnly?: boolean; cascading?: boolean },
): string {
	const nativeOnly = opts?.nativeOnly ?? false;
	const cascading = opts?.cascading ?? false;
	const baseValue = block.getStyle(type, undefined, nativeOnly, cascading);
	const base = String(baseValue ?? (nativeOnly && !cascading ? "" : "unset"));
	const baseParts = expandBoxShorthand(base, base);
	const top = block.getStyle(`${type}Top`, undefined, nativeOnly, cascading) ?? baseParts[0];
	const right = block.getStyle(`${type}Right`, undefined, nativeOnly, cascading) ?? baseParts[1];
	const bottom = block.getStyle(`${type}Bottom`, undefined, nativeOnly, cascading) ?? baseParts[2];
	const left = block.getStyle(`${type}Left`, undefined, nativeOnly, cascading) ?? baseParts[3];
	const sTop = String(top);
	const sRight = String(right);
	const sBottom = String(bottom);
	const sLeft = String(left);
	if (sTop === baseParts[0] && sRight === baseParts[1] && sBottom === baseParts[2] && sLeft === baseParts[3]) {
		return base;
	}
	// A side left unset while others are set falls back to an empty base; treat it as 0
	// so the reconstructed shorthand stays well-formed and expands to the right corners.
	const fill = (value: string) => value || "0px";
	return collapseBoxShorthand([fill(sTop), fill(sRight), fill(sBottom), fill(sLeft)]);
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

/**
 * Splits a CSS value list on whitespace, ignoring whitespace inside
 * parentheses so functional values like `calc(10px + 5%)` stay intact.
 */
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

/**
 * Expands a CSS box shorthand (margin, padding, border-radius) into its four
 * component values following the standard 1/2/3/4-value rules.
 * @param value - Shorthand value string
 * @param fallback - Value used for every side when the shorthand is empty
 * @returns Array of exactly four side values
 */
function expandBoxShorthand(value: unknown, fallback = "0"): string[] {
	const parts = splitCssValueList(String(value ?? "").trim());
	if (!parts.length) return Array(4).fill(fallback);
	if (parts.length === 1) return Array(4).fill(parts[0]);
	if (parts.length === 2) return [parts[0], parts[1], parts[0], parts[1]];
	if (parts.length === 3) return [parts[0], parts[1], parts[2], parts[1]];
	return parts.slice(0, 4);
}

/**
 * Collapses four side values into the shortest shorthand that expands back to them.
 * @param parts - Four side values, in the order expandBoxShorthand returns
 * @returns Shorthand value string
 */
function collapseBoxShorthand(parts: unknown[]): string {
	const [top, right, bottom, left] = parts.map((part) => String(part ?? ""));
	if (top === right && top === bottom && top === left) return top;
	if (top === bottom && right === left) return `${top} ${right}`;
	if (right === left) return `${top} ${right} ${bottom}`;
	return [top, right, bottom, left].join(" ");
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
	expandBoxShorthand,
	extractNumberAndUnit,
	getBoxSpacing,
	getNumberFromPx,
	normalizeValueWithUnits,
	parseAndSetBackground,
	removeDefaultUnit,
	setBoxSpacing,
	shortenNumber,
};
