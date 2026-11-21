// Pins are read from a block's own CSS, so raw CSS, AI output and breakpoint overrides
// round-trip. On each axis a block is pinned to its start side (left/top), its end side
// (right/bottom), both (stretched, size auto), or centred with left: 50% and
// `translate: -50%`. The individual translate property leaves rotate, transform and
// margins to the rest of the editor, and -50% is always half the block's own size.

import { addPxToNumber, toUnitOf } from "@/utils/cssUtils";
import {
	CENTER_SHIFT,
	centerOffset,
	centerTranslate,
	centerValue,
	isCenterValue,
	isSet,
	parseTranslate,
	readSide,
	shiftInset,
	SIDES,
	type Shift,
	type Side,
	type StyleReader,
} from "@/utils/positionValues";

type Axis = "x" | "y";
type Edge = "start" | "end";
type AxisPin = Edge | "stretch" | "center" | "none";
// a property set to null is unset
type StylePatch = Record<string, string | null>;
type AxisChange = { pin: AxisPin; styles: StylePatch };

// one axis of a positioned block, in px
type AxisBox = {
	// distances from the containing block's padding edges, before any translate
	start: number;
	end: number;
	// border box
	size: number;
	marginStart: number;
	marginEnd: number;
	container: number;
};
type Box = Record<Axis, AxisBox>;

const AXIS_SIDES = {
	x: { start: "left", end: "right", size: "width" },
	y: { start: "top", end: "bottom", size: "height" },
} as const;
const PIN_PROPERTIES = [...SIDES, "inset", "width", "height", "translate", "transform"];

class BlockPins {
	readonly x: AxisPins;
	readonly y: AxisPins;
	// moved by a translate or transform the pins did not write, which is left alone
	readonly custom: boolean;

	constructor(read: StyleReader) {
		const readPin = (property: string) => readSide(read, property);
		const shift = parseTranslate(read("translate"));
		const centered = {
			x: shift?.[0] === CENTER_SHIFT && isCenterValue(readPin("left")) && !isSet(readPin("right")),
			y: shift?.[1] === CENTER_SHIFT && isCenterValue(readPin("top")) && !isSet(readPin("bottom")),
		};
		this.custom =
			!shift ||
			/translate/i.test(String(read("transform") ?? "")) ||
			(shift[0] !== "0" && !centered.x) ||
			(shift[1] !== "0" && !centered.y);
		this.x = new AxisPins("x", readPin, centered.x && !this.custom);
		this.y = new AxisPins("y", readPin, centered.y && !this.custom);
	}

	axis(axis: Axis) {
		return axis === "x" ? this.x : this.y;
	}

	toggle(axis: Axis, edge: Edge, box: Box) {
		return this.combine({ [axis]: this.axis(axis).toggle(edge, box[axis]) });
	}

	toggleCenter(axis: Axis, box: Box) {
		return this.combine({ [axis]: this.axis(axis).toggleCenter(box[axis]) });
	}

	// a value typed into a side's field: it pins that side, and an empty one unpins it
	setSide(side: Side, value: string | null, box: Box | null) {
		const axis = axisOf(side);
		return this.combine({ [axis]: this.axis(axis).setEdge(edgeOf(side), value, box?.[axis]) });
	}

	// pins each axis as given and keeps the block where it is
	place(pins: Record<Axis, AxisPin>, box: Box) {
		return this.combine({ x: this.x.place(pins.x, box.x), y: this.y.place(pins.y, box.y) });
	}

	fill(): StylePatch {
		const fill = (axis: AxisPins) => ({ pin: "stretch" as const, styles: axis.fill() });
		return this.combine({ x: fill(this.x), y: fill(this.y) });
	}

	center(box: Box | null) {
		const center = (axis: AxisPins, axisBox?: AxisBox) => ({
			pin: "center" as const,
			styles: axis.center(axisBox),
		});
		return this.combine({ x: center(this.x, box?.x), y: center(this.y, box?.y) });
	}

	clear(): StylePatch {
		const clear = (axis: AxisPins) => ({ pin: "none" as const, styles: axis.clear() });
		return this.combine({ x: clear(this.x), y: clear(this.y) });
	}

	// moves the pinned sides, so a right-pinned block changes `right`
	moveBy(x: Shift, y: Shift, box: Box | null): StylePatch {
		return { ...this.x.moveBy(x, box?.x), ...this.y.moveBy(y, box?.y) };
	}

	// `startMove` is how far the box's left/top edge moves, `growth` how much its size changes
	resizeBy(startMove: Record<Axis, Shift>, growth: Record<Axis, Shift>, box: Box | null): StylePatch {
		return {
			...this.x.resizeBy(startMove.x, growth.x, box?.x),
			...this.y.resizeBy(startMove.y, growth.y, box?.y),
		};
	}

	// translate follows the centred axes, unless it was written by someone else
	private combine(changes: Partial<Record<Axis, AxisChange>>): StylePatch {
		const patch = { ...changes.x?.styles, ...changes.y?.styles };
		if (this.custom) return patch;
		const isCentered = (axis: Axis) => (changes[axis]?.pin ?? this.axis(axis).pin) === "center";
		const translate = centerTranslate(isCentered("x"), isCentered("y"));
		if (translate !== centerTranslate(this.x.pin === "center", this.y.pin === "center")) {
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
	) {
		const { start, end } = this.sides;
		this.pin = centered ? "center" : pinOfEdges(isSet(read(start)), isSet(read(end)));
	}

	get sides() {
		return AXIS_SIDES[this.axis];
	}

	isPinned(edge: Edge) {
		return hasEdge(this.pin, edge);
	}

	toggle(edge: Edge, box: AxisBox) {
		const change = this.place(toggledPin(this.pin, edge), box);
		// a side that stays pinned keeps its value as written
		(["start", "end"] as Edge[])
			.filter((kept) => this.isPinned(kept) && hasEdge(change.pin, kept))
			.forEach((kept) => delete change.styles[this.sides[kept]]);
		return change;
	}

	toggleCenter(box: AxisBox) {
		return this.place(this.pin === "center" ? "start" : "center", box);
	}

	place(pin: AxisPin, box: AxisBox): AxisChange {
		const { start, end, size } = this.sides;
		// the edges as seen, without the centring shift this axis may have now
		const shift = this.pin === "center" ? box.size / 2 : 0;
		const seenStart = box.start - shift;
		const seenEnd = box.end + shift;
		const styles: StylePatch = { [start]: null, [end]: null };
		if (pin === "start" || pin === "stretch") styles[start] = this.format(start, seenStart, box);
		if (pin === "end" || pin === "stretch") styles[end] = this.format(end, seenEnd, box);
		if (pin === "center") styles[start] = centerValue(seenStart + box.size / 2 - box.container / 2);
		if (pin === "stretch") styles[size] = null;
		else if (this.keepsSize(pin, { ...box, start: seenStart, end: seenEnd })) {
			styles[size] = addPxToNumber(box.size);
		}
		return { pin, styles };
	}

	setEdge(edge: Edge, value: string | null, box?: AxisBox): AxisChange {
		const side = this.sides[edge];
		const otherSide = this.sides[edge === "start" ? "end" : "start"];
		if (!value) {
			if (!this.isPinned(edge)) return { pin: this.pin, styles: {} };
			return box ? this.toggle(edge, box) : { pin: this.pin, styles: { [side]: null } };
		}
		if (this.isPinned(edge)) return { pin: this.pin, styles: { [side]: value } };
		if (this.isPinned(edge === "start" ? "end" : "start")) {
			return { pin: "stretch", styles: { [side]: value, [this.sides.size]: null } };
		}
		return { pin: edge, styles: { [side]: value, [otherSide]: null } };
	}

	fill(): StylePatch {
		const { start, end, size } = this.sides;
		return { [start]: "0px", [end]: "0px", [size]: null };
	}

	center(box?: AxisBox): StylePatch {
		const { start, end, size } = this.sides;
		const styles: StylePatch = { [start]: "50%", [end]: null };
		if (box && this.keepsSize("center", { ...box, start: (box.container - box.size) / 2 })) {
			styles[size] = addPxToNumber(box.size);
		}
		return styles;
	}

	clear(): StylePatch {
		return { [this.sides.start]: null, [this.sides.end]: null };
	}

	moveBy(shift: Shift, box?: AxisBox): StylePatch {
		if (this.pin === "center") {
			return { [this.sides.start]: centerValue(centerOffset(this.read(this.sides.start)) + shift.px) };
		}
		return this.shiftEdges(shift, shift, box);
	}

	// a centred block grows around its centre, so its offset stays
	resizeBy(startMove: Shift, growth: Shift, box?: AxisBox): StylePatch {
		if (this.pin === "center") return {};
		const endMove = { px: startMove.px + growth.px, percent: startMove.percent + growth.percent };
		return this.shiftEdges(startMove, endMove, box);
	}

	private shiftEdges(startMove: Shift, endMove: Shift, box?: AxisBox): StylePatch {
		const { start, end } = this.sides;
		const negate = ({ px, percent }: Shift) => ({ px: -px, percent: -percent });
		const styles: StylePatch = {};
		// an unpinned block sits where it is and gets pinned to its start; a side that
		// doesn't move keeps its value as written
		if (startMove.px && (this.isPinned("start") || this.pin === "none")) {
			styles[start] = shiftInset(this.read(start), startMove, box?.start);
		}
		if (endMove.px && this.isPinned("end")) {
			styles[end] = shiftInset(this.read(end), negate(endMove), box?.end);
		}
		return styles;
	}

	// pinned to one side, an auto size would shrink to fit the space left on the other
	private keepsSize(pin: AxisPin, box: AxisBox) {
		if (this.pin === "stretch") return true;
		if (this.axis === "y" || isSet(this.read(this.sides.size))) return false;
		const startInset = pin === "center" ? box.start + box.size / 2 : pin === "end" ? box.end : box.start;
		return box.marginStart + box.size + box.marginEnd > box.container - startInset + 0.5;
	}

	// a side keeps the unit it, or the other side of its axis, is written in
	private format(side: string, px: number, box: AxisBox) {
		const { start, end } = this.sides;
		const unitOf =
			this.pin === "center" ? undefined : [side, side === start ? end : start].map(this.read).find(isSet);
		return toUnitOf(unitOf, px, box.container);
	}
}

function axisOf(side: Side): Axis {
	return side === "left" || side === "right" ? "x" : "y";
}

function edgeOf(side: Side): Edge {
	return side === "left" || side === "top" ? "start" : "end";
}

function hasEdge(pin: AxisPin, edge: Edge) {
	return pin === edge || pin === "stretch";
}

function pinOfEdges(start: boolean, end: boolean): AxisPin {
	if (start && end) return "stretch";
	return start ? "start" : end ? "end" : "none";
}

// a block is never left without pins: dropping the last one centres it
function toggledPin(pin: AxisPin, edge: Edge): AxisPin {
	const other = edge === "start" ? "end" : "start";
	if (pin === "stretch") return other;
	if (pin === edge) return "center";
	return pin === other ? "stretch" : edge;
}

export { AXIS_SIDES, axisOf, BlockPins, edgeOf, PIN_PROPERTIES };
export type { Axis, AxisBox, AxisPin, Box, Edge, StylePatch };
