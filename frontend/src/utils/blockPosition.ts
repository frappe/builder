import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import {
	BlockPins,
	isSet,
	type Axis,
	type AxisBox,
	type Box,
	type Shift,
	type Side,
	type StylePatch,
} from "@/utils/positionPins";

const PIN_PROPERTIES = [
	"left",
	"right",
	"top",
	"bottom",
	"width",
	"height",
	"translate",
	"transform",
	"position",
];

// Position edits for one block, at the active breakpoint and state. The Position panel,
// canvas drag, resize and duplicate all go through here, so the pins stay in step.
class BlockPosition {
	constructor(
		private block: Block,
		private element: HTMLElement | null = findBlockElement(block),
	) {}

	private read = (property: string) => this.block.getActiveStyleValue(property as styleProperty);

	get pins() {
		return new BlockPins(this.read);
	}

	toggle(side: Side) {
		const box = this.measure();
		if (box) this.apply(this.pins.toggle(side, box));
	}

	toggleCenter(axes: Axis[]) {
		const box = this.measure();
		if (box) this.apply(this.pins.toggleCenter(axes, box));
	}

	// false when the edit is refused, as clearing the last pin on an axis is
	setSide(side: Side, value: string | null) {
		const patch = this.pins.setSide(side, value, this.measure());
		this.apply(patch);
		return Object.keys(patch).length > 0;
	}

	// leaving Free or Fixed, the centring the pins wrote at any breakpoint would shift the block in flow
	dropCentering() {
		const breakpoints = {
			desktop: this.block.baseStyles,
			tablet: this.block.tabletStyles,
			mobile: this.block.mobileStyles,
		};
		Object.entries(breakpoints).forEach(([breakpoint, styles]) => {
			const pins = new BlockPins((property) => this.block.getStyle(property as styleProperty, breakpoint));
			const sides = [pins.x.pin === "center" && "left", pins.y.pin === "center" && "top"].filter(Boolean);
			if (pins.custom || !sides.length) return;
			[...sides, "translate"].forEach((property) => delete styles[property as styleProperty]);
		});
	}

	// moves from where the block was when the move started, so a drag doesn't drift
	startMove() {
		const pins = this.snapshot();
		const box = this.measure();
		return (dx: number, dy: number) => this.apply(pins.moveBy(toShift(dx, box?.x), toShift(dy, box?.y), box));
	}

	startResize() {
		const pins = this.snapshot();
		const box = this.measure();
		const shifts = (px: Record<Axis, number>) => ({ x: toShift(px.x, box?.x), y: toShift(px.y, box?.y) });
		return {
			stretched: { x: pins.x.pin === "stretch", y: pins.y.pin === "stretch" },
			centered: { x: pins.x.pin === "center", y: pins.y.pin === "center" },
			resize: (startMove: Record<Axis, number>, growth: Record<Axis, number>) =>
				this.apply(pins.resizeBy(shifts(startMove), shifts(growth), box)),
		};
	}

	apply(patch: StylePatch) {
		Object.entries(patch).forEach(([property, value]) => {
			this.block.setActiveStyle(property as styleProperty, value);
			// clearing at tablet or mobile only drops the override, so a value a wider
			// breakpoint sets is overridden instead
			const neutral = property === "translate" ? "none" : "auto";
			const inherited = this.read(property);
			if (value === null && isSet(inherited) && inherited !== neutral) {
				this.block.setActiveStyle(property as styleProperty, neutral);
			}
		});
	}

	// the block's box in its containing block: the parent's padding box for Free, the canvas
	// frame (the window, once published) for Fixed
	measure(): Box | null {
		const element = this.element;
		const container = (element?.offsetParent || element?.closest(".canvas")) as HTMLElement | null;
		if (!element?.isConnected || !container) return null;
		const style = getComputedStyle(element);
		const px = (value: string) => parseFloat(value) || 0;
		// offsetWidth rounds to whole px, and a text block given a rounded-down width wraps
		const exact = (value: string, rounded: number) =>
			(style.boxSizing === "border-box" && px(value)) || rounded;
		const axisBox = (
			start: string,
			size: number,
			container: number,
			marginStart: string,
			marginEnd: string,
		) => {
			const margins = px(marginStart) + px(marginEnd);
			// worked out rather than read, as CSS reports the end side as written when a size overrides it
			return {
				start: px(start),
				end: container - px(start) - size - margins,
				size,
				container,
				marginStart: px(marginStart),
				marginEnd: px(marginEnd),
			};
		};
		return {
			x: axisBox(
				style.left,
				exact(style.width, element.offsetWidth),
				container.clientWidth,
				style.marginLeft,
				style.marginRight,
			),
			y: axisBox(
				style.top,
				exact(style.height, element.offsetHeight),
				container.clientHeight,
				style.marginTop,
				style.marginBottom,
			),
		};
	}

	private snapshot() {
		const values = Object.fromEntries(PIN_PROPERTIES.map((property) => [property, this.read(property)]));
		return new BlockPins((property) => values[property]);
	}
}

function findBlockElement(block: Block) {
	const breakpoint = useCanvasStore().activeCanvas?.activeBreakpoint || "desktop";
	return document.querySelector<HTMLElement>(
		`.canvas [data-block-id="${block.blockId}"][data-breakpoint="${breakpoint}"]`,
	);
}

// NaN in % when the container has no size to measure it by
function toShift(px: number, box?: AxisBox): Shift {
	if (!box) return { px, percent: 0 };
	return { px, percent: box.container ? (px / box.container) * 100 : NaN };
}

export default BlockPosition;
