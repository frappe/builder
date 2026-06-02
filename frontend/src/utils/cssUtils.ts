// CSS value parsing / normalization helpers (px, spacing shorthand, background).
// Extracted from helpers.ts; re-exported there for backwards compatibility.

import Block from "@/block";

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
	if (!value) return;
	const arr = value.split(" ");
	if (arr.length === 1) {
		block.setStyle(type, arr[0]);
	} else if (arr.length === 2) {
		block.setStyle(`${type}Top`, arr[0]);
		block.setStyle(`${type}Bottom`, arr[0]);
		block.setStyle(`${type}Left`, arr[1]);
		block.setStyle(`${type}Right`, arr[1]);
	} else if (arr.length === 3) {
		block.setStyle(`${type}Top`, arr[0]);
		block.setStyle(`${type}Left`, arr[1]);
		block.setStyle(`${type}Right`, arr[1]);
		block.setStyle(`${type}Bottom`, arr[2]);
	} else if (arr.length === 4) {
		block.setStyle(`${type}Top`, arr[0]);
		block.setStyle(`${type}Right`, arr[1]);
		block.setStyle(`${type}Bottom`, arr[2]);
		block.setStyle(`${type}Left`, arr[3]);
	}
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
	const top = block.getStyle(`${type}Top`, undefined, nativeOnly, cascading) ?? base;
	const bottom = block.getStyle(`${type}Bottom`, undefined, nativeOnly, cascading) ?? base;
	const left = block.getStyle(`${type}Left`, undefined, nativeOnly, cascading) ?? base;
	const right = block.getStyle(`${type}Right`, undefined, nativeOnly, cascading) ?? base;
	const sTop = String(top);
	const sBottom = String(bottom);
	const sLeft = String(left);
	const sRight = String(right);
	if (sTop === base && sBottom === base && sLeft === base && sRight === base) return base;
	if (sTop === sBottom && sTop === sRight && sTop === sLeft) return sTop;
	if (sTop === sBottom && sLeft === sRight) return `${sTop} ${sLeft}`;
	return `${sTop} ${sRight} ${sBottom} ${sLeft}`;
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
	const match = numberStr.match(/^([0-9.]+)([a-z%]*)$/);
	if (match) {
		const [, number, existingUnit] = match;
		return existingUnit ? numberStr : number + unit;
	}
	return numberStr;
}

/**
 * Normalizes CSS values by adding default units where missing
 * Handles both single values and spacing properties with multiple values
 * @param value - CSS value string
 * @param unitOptions - Array of possible units, first is used as default
 * @param propertyKey - CSS property name (used to detect spacing properties)
 * @returns Normalized value string with units added
 */
function normalizeValueWithUnits(value: string, unitOptions: string[], propertyKey: string): string {
	if (!unitOptions.length) return value;

	const defaultUnit = unitOptions[0];
	const isSpacingProperty = propertyKey === "margin" || propertyKey === "padding";

	if (isSpacingProperty) {
		const parts = value.trim().split(/\s+/);
		if (parts.length > 1) {
			return parts.map((part) => addUnitToNumber(part, defaultUnit)).join(" ");
		}
	}

	return addUnitToNumber(value, defaultUnit);
}

export {
	addPxToNumber,
	addUnitToNumber,
	extractNumberAndUnit,
	getBoxSpacing,
	getNumberFromPx,
	normalizeValueWithUnits,
	parseAndSetBackground,
	parseBackground,
	setBoxSpacing,
	shortenNumber,
};
