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

	setSide(side: Side, value: string | null) {
		this.apply(this.pins.setSide(side, value, this.measure()));
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
	private measure(): Box | null {
		const element = this.element;
		const container = (element?.offsetParent || element?.closest(".canvas")) as HTMLElement | null;
		if (!element?.isConnected || !container) return null;
		const style = getComputedStyle(element);
		const px = (value: string) => parseFloat(value) || 0;
		return {
			x: {
				start: px(style.left),
				end: px(style.right),
				size: element.offsetWidth,
				container: container.clientWidth,
			},
			y: {
				start: px(style.top),
				end: px(style.bottom),
				size: element.offsetHeight,
				container: container.clientHeight,
			},
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
