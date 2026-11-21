// A free block's pins, read from its own CSS, so raw CSS, AI output and breakpoint overrides
// round-trip. Each axis is pinned to its start side (left/top), its end side (right/bottom),
// both (stretched, size auto), or centred with `left: 50%` and `translate: -50%`.

import { addPxToNumber, toUnitOf } from "@/utils/cssUtils";

type Axis = "x" | "y";
type Edge = "start" | "end";
type Side = "top" | "right" | "bottom" | "left";
type AxisPin = Edge | "stretch" | "center" | "none";
// a property set to null is unset
type StylePatch = Record<string, string | null>;
type StyleReader = (property: string) => StyleValue | undefined;
// one axis of the block in its containing block, in px, before any centring translate
type AxisBox = {
	start: number;
	end: number;
	size: number;
	container: number;
	marginStart: number;
	marginEnd: number;
};
type Box = Record<Axis, AxisBox>;
// a move in px, and the same move as a % of the container, for a side written in %
type Shift = { px: number; percent: number };
type AxisChange = { pin: AxisPin; styles: StylePatch };

const AXIS_SIDES = {
	x: { start: "left", end: "right", size: "width" },
	y: { start: "top", end: "bottom", size: "height" },
} as const;
// the translates centring writes, and the axes each centres
const CENTER_TRANSLATES: Record<string, [boolean, boolean]> = {
	"": [false, false],
	none: [false, false],
	"-50%": [true, false],
	"-50% 0": [true, false],
	"0 -50%": [false, true],
	"-50% -50%": [true, true],
};
// the axis and edge each side pins
const SIDE_PINS = {
	top: ["y", "start"],
	right: ["x", "end"],
	bottom: ["y", "end"],
	left: ["x", "start"],
} as const satisfies Record<Side, [Axis, Edge]>;
const CENTER_OFFSET = /^calc\(50% ([+-]) (\d*\.?\d+)px\)$/;
const LENGTH = /^(-?\d*\.?\d+)(px|%)?$/;
const CALC_OFFSET = /^calc\((.+) ([+-]) (\d*\.?\d+)px\)$/;

class BlockPins {
	readonly x: AxisPins;
	readonly y: AxisPins;
	// moved by a translate or transform the pins didn't write, so centring is off
	readonly custom: boolean;

	constructor(read: StyleReader) {
		const shift = CENTER_TRANSLATES[String(read("translate") ?? "").trim()];
		const centered = [isCenterValue(read("left")), isCenterValue(read("top"))];
		this.custom =
			!shift ||
			/translate/i.test(String(read("transform") ?? "")) ||
			shift.some((axisShift, index) => axisShift && !centered[index]);
		// a fixed block's frame in the editor is as tall as the page, not the window
		const inWindow = read("position") === "fixed";
		this.x = new AxisPins("x", read, Boolean(shift?.[0]) && !this.custom, false);
		this.y = new AxisPins("y", read, Boolean(shift?.[1]) && !this.custom, inWindow);
	}

	axis(axis: Axis) {
		return axis === "x" ? this.x : this.y;
	}

	isPinned(side: Side) {
		const [axis, edge] = SIDE_PINS[side];
		return this.axis(axis).isPinned(edge);
	}

	toggle(side: Side, box: Box) {
		const [axis, edge] = SIDE_PINS[side];
		return this.combine({ [axis]: this.axis(axis).toggle(edge, box[axis]) });
	}

	// a line of the plus centres its axis and the dot both; once all are centred they go
	// back to their start sides, where the block shows
	toggleCenter(axes: Axis[], box: Box) {
		const center = !axes.every((axis) => this.axis(axis).pin === "center");
		const changes = axes.map((axis) => [axis, this.axis(axis).setCentered(center, box[axis])]);
		return this.combine(Object.fromEntries(changes));
	}

	setSide(side: Side, value: string | null, box: Box | null) {
		const [axis, edge] = SIDE_PINS[side];
		return this.combine({ [axis]: this.axis(axis).setEdge(edge, value, box?.[axis]) });
	}

	moveBy(x: Shift, y: Shift, box: Box | null): StylePatch {
		return { ...this.x.moveBy(x, box?.x), ...this.y.moveBy(y, box?.y) };
	}

	// `startMove` is how far the left/top edge moves, `growth` how much the size changes
	resizeBy(startMove: Record<Axis, Shift>, growth: Record<Axis, Shift>, box: Box | null): StylePatch {
		return {
			...this.x.resizeBy(startMove.x, growth.x, box?.x),
			...this.y.resizeBy(startMove.y, growth.y, box?.y),
		};
	}

	// translate follows the centred axes, unless someone else wrote it
	private combine(changes: Partial<Record<Axis, AxisChange>>): StylePatch {
		const patch = { ...changes.x?.styles, ...changes.y?.styles };
		const isCentered = (axis: Axis) => (changes[axis]?.pin ?? this.axis(axis).pin) === "center";
		const translate = centerTranslate(isCentered("x"), isCentered("y"));
		if (!this.custom && translate !== centerTranslate(this.x.pin === "center", this.y.pin === "center")) {
			patch.translate = translate;
		}
		return patch;
	}
}

class AxisPins {
	readonly pin: AxisPin;

	constructor(
		readonly axis: Axis,
		private read: StyleReader,
		centered: boolean,
		private inWindow: boolean,
	) {
		const start = isSet(read(this.sides.start));
		// with a size set, CSS keeps the start side and ignores the end one
		const end = isSet(read(this.sides.end)) && !(start && isSet(read(this.sides.size)));
		this.pin = centered ? "center" : start && end ? "stretch" : start ? "start" : end ? "end" : "none";
	}

	get sides() {
		return AXIS_SIDES[this.axis];
	}

	isPinned(edge: Edge) {
		return hasEdge(this.pin, edge);
	}

	// the last pin on an axis stays, so the block never drops back to where it sat in flow
	toggle(edge: Edge, box: AxisBox): AxisChange {
		if (this.pin === edge) return { pin: this.pin, styles: {} };
		const other = edge === "start" ? "end" : "start";
		const change = this.place(this.pin === "stretch" ? other : this.isPinned(other) ? "stretch" : edge, box);
		// the side that stays pinned keeps its value as written
		if (this.isPinned(other)) delete change.styles[this.sides[other]];
		return change;
	}

	// centring goes to the exact middle; uncentring keeps the block where it shows
	setCentered(center: boolean, box: AxisBox): AxisChange {
		if (!center) return this.place("start", box);
		const { start, end } = this.sides;
		// left: 50% puts the margin edge in the middle, so the start margin is taken off
		const styles = { [start]: centerValue(-box.marginStart), [end]: null };
		return { pin: "center", styles: { ...styles, ...this.keepSize(box, true) } };
	}

	// typed into a side's field: a value pins that side, and clearing it is like clicking it
	setEdge(edge: Edge, value: string | null, box?: AxisBox): AxisChange {
		if (!isSet(value))
			return box && this.isPinned(edge) ? this.toggle(edge, box) : { pin: this.pin, styles: {} };
		const other = edge === "start" ? "end" : "start";
		const styles: StylePatch = { [this.sides[edge]]: value };
		if (this.isPinned(edge)) return { pin: this.pin, styles };
		if (this.isPinned(other)) return { pin: "stretch", styles: { ...styles, [this.sides.size]: null } };
		return { pin: edge, styles: { ...styles, [this.sides[other]]: null } };
	}

	moveBy(shift: Shift, box?: AxisBox): StylePatch {
		if (this.pin !== "center") return this.shiftEdges(shift, shift, box);
		const { start } = this.sides;
		return { [start]: centerValue(centerOffset(this.read(start)) + shift.px) };
	}

	// a centred block grows around its centre, so it keeps its offset
	resizeBy(startMove: Shift, growth: Shift, box?: AxisBox): StylePatch {
		if (this.pin === "center") return {};
		const endMove = { px: startMove.px + growth.px, percent: startMove.percent + growth.percent };
		return this.shiftEdges(startMove, endMove, box);
	}

	// pins the axis as `pin`, keeping the block where it shows
	private place(pin: AxisPin, box: AxisBox): AxisChange {
		const styles = this.inWindow ? this.carry(pin, box) : this.measured(pin, box);
		Object.assign(styles, pin === "stretch" ? { [this.sides.size]: null } : this.keepSize(box));
		return { pin, styles };
	}

	private measured(pin: AxisPin, box: AxisBox): StylePatch {
		const { start, end } = this.sides;
		const shift = this.pin === "center" ? box.size / 2 : 0;
		return {
			[start]: hasEdge(pin, "start") ? this.format(start, box.start - shift, box) : null,
			[end]: hasEdge(pin, "end") ? this.format(end, box.end + shift, box) : null,
		};
	}

	// A Fixed block's vertical sides can't be measured in the editor, whose frame is as tall as
	// the page, so a side it gets pinned to takes the distance of the side it joins or
	// replaces; out of the middle it keeps where it shows, and with no pin it starts at the edge.
	private carry(pin: AxisPin, box: AxisBox): StylePatch {
		const { start, end } = this.sides;
		const distance = (edge: Edge) => {
			if (this.pin === "center") return this.offCenter(edge, box);
			if (this.pin === "none") return edge === "start" ? addPxToNumber(box.start) : "0px";
			return String(this.read(this.isPinned("start") ? start : end));
		};
		return {
			[start]: hasEdge(pin, "start") ? distance("start") : null,
			[end]: hasEdge(pin, "end") ? distance("end") : null,
		};
	}

	// The `edge` side of a centred block, where it shows. A size set relative to the window
	// stays a length the window resolves, as the editor's page-tall frame would measure it.
	private offCenter(edge: Edge, box: AxisBox) {
		const offset = centerOffset(this.read(this.sides.start));
		const shift = edge === "start" ? offset : -offset - box.marginStart - box.marginEnd;
		const size = String(this.read(this.sides.size) ?? "");
		if (!isSet(size) || /content|^-?\d*\.?\d+px$/.test(size)) return centerValue(shift - box.size / 2);
		return `calc(${addOffset("50%", shift).replace(/^calc\((.*)\)$/, "$1")} - (${length(size)}) / 2)`;
	}

	// Out of a stretch an auto size would shrink to its content, and centred an auto or
	// fit-content width to the half of the container right of the middle.
	private keepSize(box: AxisBox, centring = false): StylePatch {
		const { start, end, size } = this.sides;
		const value = this.read(size);
		if (this.pin === "stretch") {
			if (isSet(value)) return {};
			// a Fixed block's height comes from the window, which the editor's page-tall frame isn't
			if (this.inWindow)
				return { [size]: `calc(100% - ${length(this.read(start))} - ${length(this.read(end))})` };
			return { [size]: exactPx(box.size) };
		}
		const shrinks = centring && this.axis === "x" && (!isSet(value) || /content/.test(String(value)));
		return shrinks ? { [size]: exactPx(box.size) } : {};
	}

	// moves the pinned sides; an unpinned axis gets pinned to its start
	private shiftEdges(startMove: Shift, endMove: Shift, box?: AxisBox): StylePatch {
		const { start, end } = this.sides;
		const styles: StylePatch = {};
		if (this.pin !== "end") styles[start] = shiftSide(this.read(start), startMove, box?.start);
		if (this.isPinned("end")) {
			styles[end] = shiftSide(this.read(end), { px: -endMove.px, percent: -endMove.percent }, box?.end);
		}
		return styles;
	}

	// a side keeps the unit it, or the other side of its axis, is written in
	private format(side: string, px: number, box: AxisBox) {
		const { start, end } = this.sides;
		const unitOf =
			this.pin === "center" ? undefined : [side, side === start ? end : start].map(this.read).find(isSet);
		return toUnitOf(unitOf, px, box.container);
	}
}

function hasEdge(pin: AxisPin, edge: Edge) {
	return pin === edge || pin === "stretch";
}

// auto, initial and unset all leave an inset unpinned
function isSet(value: StyleValue | undefined) {
	return value !== undefined && value !== null && !/^\s*(auto|initial|unset)?\s*$/i.test(String(value));
}

function centerTranslate(x: boolean, y: boolean) {
	return x || y ? `${x ? "-50%" : "0"} ${y ? "-50%" : "0"}` : null;
}

function isCenterValue(value: StyleValue | undefined) {
	const text = String(value ?? "").trim();
	return text === "50%" || CENTER_OFFSET.test(text);
}

function centerOffset(value: StyleValue | undefined) {
	const match = String(value ?? "")
		.trim()
		.match(CENTER_OFFSET);
	return match ? (match[1] === "-" ? -1 : 1) * Number(match[2]) : 0;
}

// to a tenth of a px, as a block of odd size sits half a px off any whole px
function centerValue(offset: number) {
	const px = Math.round(offset * 10) / 10;
	return px ? `calc(50% ${px < 0 ? "-" : "+"} ${Math.abs(px)}px)` : "50%";
}

// a unitless number, which calc() won't take, in px
function length(value: StyleValue | undefined) {
	const text = String(value ?? "").trim();
	return /^-?\d*\.?\d+$/.test(text) ? `${text}px` : text;
}

// a size a text block wraps at if rounded down, so rounded up to a hundredth
function exactPx(px: number) {
	return `${Math.ceil(px * 100) / 100}px`;
}

// A px or % side moves in its own unit, and any other length (calc, em, vh) gets the move
// added in px. An unpinned side, or a % with no container to measure it by, starts from
// the measured px.
function shiftSide(value: StyleValue | undefined, shift: Shift, measured = 0) {
	const text = String(value ?? "").trim();
	const match = text.match(LENGTH);
	if (match?.[2] === "%" && !isNaN(shift.percent)) {
		return `${Math.round((Number(match[1]) + shift.percent) * 10) / 10}%`;
	}
	if (match || !isSet(text)) {
		return addPxToNumber((match && match[2] !== "%" ? Number(match[1]) : measured) + shift.px);
	}
	return addOffset(text, shift.px);
}

// `px` added to a length, folded into the trailing `± Npx` of a calc() so drags don't nest
function addOffset(text: string, px: number) {
	const match = text.match(CALC_OFFSET);
	const base = match ? match[1] : text;
	const offset = Math.round(((match ? Number(match[2] + match[3]) : 0) + px) * 10) / 10;
	if (offset) return `calc(${base} ${offset < 0 ? "-" : "+"} ${Math.abs(offset)}px)`;
	return LENGTH.test(base) || base.startsWith("calc(") ? base : `calc(${base})`;
}

export { BlockPins, isSet, SIDE_PINS };
export type { Axis, AxisBox, Box, Edge, Shift, Side, StylePatch };
