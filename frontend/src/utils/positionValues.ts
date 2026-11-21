// The CSS values pins are read from and written as: insets, the centring calc and translate.

import { addPxToNumber } from "@/utils/cssUtils";

type Side = "top" | "right" | "bottom" | "left";
type StyleReader = (property: string) => StyleValue | undefined;
// how far a move goes on a side written in px, and on one written in %
type Shift = { px: number; percent: number };

const SIDES: Side[] = ["top", "right", "bottom", "left"];
const CENTER_SHIFT = "-50%";
// a centred block this close to the middle is put back on plain 50%
const CENTER_SNAP = 2;
const CENTER_OFFSET = /^calc\(50% ([+-]) (\d*\.?\d+)px\)$/;
const PLAIN_LENGTH = /^(-?\d*\.?\d+)(px|%)?$/;

// a side's own value, or the one an `inset` shorthand gives it
function readSide(read: StyleReader, property: string) {
	const value = read(property);
	if (!isEmpty(value) || !SIDES.includes(property as Side)) return value;
	return parseInset(read("inset"))?.[property as Side];
}

function isSet(value: StyleValue | undefined) {
	return !isEmpty(value) && value !== "auto";
}

function isEmpty(value: StyleValue | undefined) {
	return value === undefined || value === null || value === "";
}

function centerTranslate(x: boolean, y: boolean) {
	if (!x && !y) return null;
	return `${x ? CENTER_SHIFT : "0"} ${y ? CENTER_SHIFT : "0"}`;
}

function centerValue(offset: number) {
	if (Math.abs(offset) < CENTER_SNAP) return "50%";
	return `calc(50% ${offset < 0 ? "-" : "+"} ${Math.abs(Math.round(offset))}px)`;
}

function isCenterValue(value: StyleValue | undefined) {
	const text = String(value ?? "").trim();
	return text === "50%" || CENTER_OFFSET.test(text);
}

function centerOffset(value: StyleValue | undefined) {
	const match = String(value ?? "")
		.trim()
		.match(CENTER_OFFSET);
	if (!match) return 0;
	return (match[1] === "-" ? -1 : 1) * Number(match[2]);
}

// a px or % side moves in its own unit; anything else (em, calc, auto) restarts in px
function shiftInset(value: StyleValue | undefined, shift: Shift, measured = 0) {
	const match = String(value ?? "")
		.trim()
		.match(PLAIN_LENGTH);
	if (match?.[2] === "%") return `${Math.round((Number(match[1]) + shift.percent) * 10) / 10}%`;
	return addPxToNumber((match ? Number(match[1]) : measured) + shift.px);
}

// [x, y] of a translate, with zero lengths as "0"; null for one the pins can't read
function parseTranslate(value: StyleValue | undefined): [string, string] | null {
	const text = String(value ?? "").trim();
	if (!text || text === "none") return ["0", "0"];
	const parts = text.split(/\s+/).map((part) => (/^0(px|%)?$/.test(part) ? "0" : part));
	if (parts.length > 3 || (parts.length === 3 && parts[2] !== "0")) return null;
	return [parts[0], parts[1] ?? "0"];
}

function parseInset(value: StyleValue | undefined): Record<Side, string> | null {
	const parts = String(value ?? "")
		.trim()
		.split(/\s+/)
		.filter(Boolean);
	if (!parts.length || parts.length > 4) return null;
	const [top, right = top, bottom = top, left = right] = parts;
	return { top, right, bottom, left };
}

export {
	CENTER_SHIFT,
	centerOffset,
	centerTranslate,
	centerValue,
	isCenterValue,
	isSet,
	parseInset,
	parseTranslate,
	readSide,
	shiftInset,
	SIDES,
};
export type { Shift, Side, StyleReader };
