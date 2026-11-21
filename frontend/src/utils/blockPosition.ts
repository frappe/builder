import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import {
	AXIS_SIDES,
	BlockPins,
	PIN_PROPERTIES,
	type Axis,
	type AxisBox,
	type Box,
	type Edge,
	type StylePatch,
} from "@/utils/positionPins";
import { isSet, parseInset, readSide, SIDES, type Shift, type Side } from "@/utils/positionValues";

const FREE_POSITIONS = ["absolute", "fixed"];
const POSITIONED = ["relative", "absolute", "fixed", "sticky"];

// Position edits for one block. The Position panel, canvas drag, resize and duplicate all go
// through here, at the active breakpoint and state, so the pins never fall out of step.
class BlockPosition {
	constructor(
		private block: Block,
		private element: HTMLElement | SVGElement | null = findBlockElement(block),
	) {}

	private read = (property: string) => this.block.getActiveStyleValue(property as styleProperty);

	get pins() {
		return new BlockPins(this.read);
	}

	toggle(axis: Axis, edge: Edge) {
		const box = this.measureToPin();
		if (box) this.apply(this.pins.toggle(axis, edge, box));
	}

	toggleCenter(axis: Axis) {
		const box = this.measureToPin();
		if (box) this.apply(this.pins.toggleCenter(axis, box));
	}

	setSide(side: Side, value: string | null) {
		this.apply(this.pins.setSide(side, value, this.measureToPin()));
	}

	fill() {
		this.apply(this.pins.fill());
	}

	center() {
		this.apply(this.pins.center(this.measureToPin()));
	}

	// a width or height typed while the axis is stretched keeps the start pin only
	releaseStretch(axis: Axis) {
		if (this.pins.axis(axis).pin !== "stretch") return;
		this.apply({ [axis === "x" ? "right" : "bottom"]: null });
	}

	moveBy(dx: number, dy: number) {
		this.startMove()(dx, dy);
	}

	// moves from where the block was when the move started, so a drag doesn't drift
	startMove() {
		const pins = this.snapshotPins();
		const box = this.measure();
		return (dx: number, dy: number) => this.apply(pins.moveBy(toShift(dx, box?.x), toShift(dy, box?.y), box));
	}

	startResize() {
		const pins = this.snapshotPins();
		const box = this.measure();
		return {
			stretched: { x: pins.x.pin === "stretch", y: pins.y.pin === "stretch" },
			centered: { x: pins.x.pin === "center", y: pins.y.pin === "center" },
			resize: (startMove: Record<Axis, number>, growth: Record<Axis, number>) => {
				const shift = (axis: Axis, px: number) => toShift(px, box?.[axis]);
				const moves = { x: shift("x", startMove.x), y: shift("y", startMove.y) };
				this.apply(pins.resizeBy(moves, { x: shift("x", growth.x), y: shift("y", growth.y) }, box));
			},
		};
	}

	// switching position keeps the block where it is, so Free and Fixed start from its spot.
	// Between Free and Fixed the pins carry over as written: where a fixed block shows in the
	// editor's frame is not where it shows in the window.
	setType(type: string) {
		const wasFree = FREE_POSITIONS.includes(String(this.block.getStyle("position")));
		const pins = this.pins;
		const box = FREE_POSITIONS.includes(type) && !wasFree ? this.measureAs(type) : null;
		this.writePosition(type);
		if (type === "absolute") this.positionParent();
		if (box) this.apply(this.placeFree(pins, box));
		else if (type === "sticky") this.makeSticky(wasFree);
		else if (!FREE_POSITIONS.includes(type)) this.apply(pins.clear());
	}

	apply(patch: StylePatch) {
		if (SIDES.some((side) => side in patch)) this.expandInset();
		Object.entries(patch).forEach(([property, value]) => this.write(property, value));
	}

	// clearing at tablet or mobile only drops the override, so a value a wider breakpoint
	// sets is overridden with `auto` (or `none`) instead
	private write(property: string, value: string | null) {
		this.block.setActiveStyle(property as styleProperty, value);
		if (value !== null) return;
		const neutral = property === "translate" ? "none" : "auto";
		const inherited = readSide(this.read, property);
		if (isSet(inherited) && inherited !== neutral) {
			this.block.setActiveStyle(property as styleProperty, neutral);
		}
	}

	// the four sides are edited one by one, so an `inset` shorthand on this breakpoint becomes them
	private expandInset() {
		const property = this.block.getActiveStyleProperty("inset");
		const sides = parseInset(this.block.getStyle(property, null, true));
		if (!sides) return;
		const native = (side: Side) => this.block.getStyle(this.block.getActiveStyleProperty(side), null, true);
		const longhands = SIDES.filter((side) => !isSet(native(side)));
		this.block.setActiveStyle("inset", null);
		longhands.forEach((side) => this.block.setActiveStyle(side, sides[side]));
	}

	private snapshotPins() {
		const values = Object.fromEntries(PIN_PROPERTIES.map((property) => [property, this.read(property)]));
		return new BlockPins((property) => values[property]);
	}

	private placeFree(pins: BlockPins, box: Box) {
		const patch = pins.place({ x: "start", y: "start" }, box);
		// in flow it filled the line; out of flow an auto width would shrink to its content
		if (!isSet(this.read("width"))) patch.width = `${Math.round(box.x.size)}px`;
		return patch;
	}

	// offsets placed a free block in its parent; as sticky they would mean something else
	private makeSticky(wasFree: boolean) {
		if (wasFree) this.apply(this.pins.clear());
		if (!isSet(readSide(this.read, "top")) && !isSet(readSide(this.read, "bottom"))) {
			this.apply({ top: "0px" });
		}
	}

	private writePosition(type: string) {
		const inherited = this.block.getStyle("position", null, false, true);
		const value = type === "static" && (!inherited || inherited === "static") ? "" : type;
		this.block.setStyle("position", value);
	}

	private positionParent() {
		const parent = this.block.getParentBlock();
		if (parent && !POSITIONED.includes(String(parent.getStyle("position")))) {
			parent.setStyle("position", "relative");
		}
	}

	// the block's box in its containing block: the parent's padding box for absolute, the
	// canvas frame (the window, once published) for fixed
	measure(): Box | null {
		const element = this.element;
		if (!element?.isConnected) return null;
		const style = getComputedStyle(element);
		if (!FREE_POSITIONS.includes(style.position)) return null;
		const container = containerOf(element);
		const px = (value: string) => parseFloat(value) || 0;
		const size = sizeOf(element, style);
		return {
			x: {
				start: px(style.left),
				end: px(style.right),
				size: size.width,
				marginStart: px(style.marginLeft),
				marginEnd: px(style.marginRight),
				container: container.clientWidth,
			},
			y: {
				start: px(style.top),
				end: px(style.bottom),
				size: size.height,
				marginStart: px(style.marginTop),
				marginEnd: px(style.marginBottom),
				container: container.clientHeight,
			},
		};
	}

	// with the size a stretched axis's auto size falls back to, so unpinning a side keeps
	// a block sized by its content that way
	private measureToPin(): Box | null {
		const box = this.measure();
		const element = this.element;
		if (!box || !(element instanceof HTMLElement)) return box;
		const pins = this.pins;
		(["x", "y"] as Axis[]).forEach((axis) => {
			const { size } = AXIS_SIDES[axis];
			if (pins.axis(axis).pin === "stretch" && !isSet(this.read(size))) {
				box[axis].content = contentSize(element, size);
			}
		});
		return box;
	}

	// where the block sits now, measured in the containing block it gets as `type`
	private measureAs(type: string): Box | null {
		const element = this.element;
		if (!(element instanceof HTMLElement) || !element.isConnected) return null;
		const container = (type === "fixed" ? element.closest(".canvas") : element.parentElement) as HTMLElement;
		if (!container) return null;
		const style = getComputedStyle(element);
		const from = layoutOffset(element);
		const to = layoutOffset(container);
		const axisBox = (axis: Axis): AxisBox => {
			const x = axis === "x";
			const marginStart = parseFloat(x ? style.marginLeft : style.marginTop) || 0;
			const marginEnd = parseFloat(x ? style.marginRight : style.marginBottom) || 0;
			const size = x ? element.offsetWidth : element.offsetHeight;
			const containerSize = x ? container.clientWidth : container.clientHeight;
			const start = from[axis] - to[axis] - (x ? container.clientLeft : container.clientTop) - marginStart;
			const end = containerSize - start - marginStart - size - marginEnd;
			return { start, end, size, marginStart, marginEnd, container: containerSize };
		};
		return { x: axisBox("x"), y: axisBox("y") };
	}
}

function findBlockElement(block: Block) {
	const breakpoint = useCanvasStore().activeCanvas?.activeBreakpoint || "desktop";
	const elements = document.querySelectorAll<HTMLElement>(
		`.canvas [data-block-id="${block.blockId}"][data-breakpoint="${breakpoint}"]`,
	);
	return Array.from(elements).find((element) => element.getClientRects().length) || elements[0] || null;
}

function containerOf(element: HTMLElement | SVGElement) {
	const parent = element instanceof HTMLElement ? element.offsetParent : null;
	return (parent || element.closest(".canvas") || document.documentElement) as HTMLElement;
}

function sizeOf(element: HTMLElement | SVGElement, style: CSSStyleDeclaration) {
	if (element instanceof HTMLElement) return { width: element.offsetWidth, height: element.offsetHeight };
	return { width: parseFloat(style.width) || 0, height: parseFloat(style.height) || 0 };
}

// the border edge in layout px, ignoring transforms (the canvas zoom and any rotation)
function layoutOffset(element: HTMLElement) {
	const offset = { x: 0, y: 0 };
	for (let current: HTMLElement | null = element; current; current = current.offsetParent as HTMLElement) {
		offset.x += current.offsetLeft + (current === element ? 0 : current.clientLeft);
		offset.y += current.offsetTop + (current === element ? 0 : current.clientTop);
	}
	return offset;
}

// the size an auto width or height takes from the content, set for a moment to measure it
function contentSize(element: HTMLElement, property: "width" | "height") {
	const { style } = element;
	const [value, priority] = [style.getPropertyValue(property), style.getPropertyPriority(property)];
	style.setProperty(property, "max-content", "important");
	const size = property === "width" ? element.offsetWidth : element.offsetHeight;
	style.setProperty(property, value, priority);
	return size;
}

function toShift(px: number, box?: AxisBox): Shift {
	return { px, percent: box?.container ? (px / box.container) * 100 : 0 };
}

export default BlockPosition;
