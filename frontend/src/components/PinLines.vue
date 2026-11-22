<template>
	<div
		v-for="line in lines"
		:key="line.key"
		class="pointer-events-none absolute border-dashed border-blue-400"
		:class="line.horizontal ? 'h-0 border-t' : 'w-0 border-l'"
		:style="line.style">
		<span
			v-if="line.label"
			class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-[3px] bg-blue-500 px-1 py-0.5 text-[10px] leading-none text-white">
			{{ line.label }}
		</span>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import BlockPosition from "@/utils/blockPosition";
import type { AxisBox, BlockPins, Box, Edge } from "@/utils/positionPins";
import { getElementRotation } from "@/utils/rotation";
import { inject, nextTick, ref, watch, type CSSProperties } from "vue";

type PinLine = { key: string; horizontal: boolean; style: CSSProperties; label?: string };

const props = defineProps<{
	block: Block;
	target: HTMLElement | SVGElement;
}>();

const canvasProps = inject("canvasProps") as CanvasProps;
const lines = ref<PinLine[]>([]);

// a dashed line from each pinned edge to its containing block; a centred axis shows the
// container's centre line, and a line out to it from the block's centre when off it
const measure = () => {
	const position = new BlockPosition(props.block, props.target as HTMLElement);
	// insets ignore rotation, so a rotated block's lines would point the wrong way
	const box = getElementRotation(props.target) ? null : position.measure();
	lines.value = box ? pinLines(position.pins, box, canvasProps.scale) : [];
};

// anything in the block's or its parent's styles, in any state or breakpoint, can move a line
watch(
	() => {
		const parent = props.block.getParentBlock();
		return [props.block, parent].flatMap((block) =>
			block ? [block.baseStyles, block.tabletStyles, block.mobileStyles, block.activeState] : [],
		);
	},
	() => nextTick(measure),
	{ immediate: true, deep: true },
);
watch(
	() => canvasProps.scale,
	() => nextTick(measure),
);

function pinLines(pins: BlockPins, box: Box, scale: number) {
	// where the block's border box shows in its container, after the centring translate
	const shown = (axis: "x" | "y") =>
		box[axis].start + box[axis].marginStart - (pins.axis(axis).pin === "center" ? box[axis].size / 2 : 0);
	const guides = (["x", "y"] as const)
		.filter((axis) => pins.axis(axis).pin === "center")
		.map((axis) => centerGuide(axis, box, shown, scale));
	return [...guides, ...axisLines(pins, box.x, scale, true), ...axisLines(pins, box.y, scale, false)];
}

// the container's centre line, across the whole container
function centerGuide(axis: "x" | "y", box: Box, shown: (axis: "x" | "y") => number, scale: number): PinLine {
	const across = axis === "x" ? "y" : "x";
	const px = (value: number) => `${value * scale}px`;
	const along = { [axis === "x" ? "left" : "top"]: px(box[axis].container / 2 - shown(axis)) };
	const span = {
		[axis === "x" ? "top" : "left"]: px(-shown(across)),
		[axis === "x" ? "height" : "width"]: px(box[across].container),
	};
	return { key: `guide-${axis}`, horizontal: axis === "y", style: { ...along, ...span } };
}

// the insets stop at the margin edge, so a gap is drawn to the border
function axisLines(pins: BlockPins, box: AxisBox, scale: number, horizontal: boolean): PinLine[] {
	const axis = pins.axis(horizontal ? "x" : "y");
	if (axis.pin === "center") {
		// left: calc(50% + offset) puts the margin edge there; the translate centres the border box on it
		const offset = box.start - box.container / 2 + box.marginStart;
		return Math.abs(offset) < 1 ? [] : [line(`center-${axis.axis}`, horizontal, offset, scale, "center")];
	}
	const gap = (edge: Edge) => (edge === "start" ? box.start + box.marginStart : box.end + box.marginEnd);
	// a block that overflows its container has no gap to draw on that side
	return (["start", "end"] as Edge[])
		.filter((edge) => axis.isPinned(edge) && gap(edge) >= 1)
		.map((edge) => line(`${edge}-${axis.axis}`, horizontal, gap(edge), scale, edge));
}

function line(key: string, horizontal: boolean, length: number, scale: number, from: Edge | "center") {
	const across = horizontal ? { top: "50%" } : { left: "50%" };
	const size = { [horizontal ? "width" : "height"]: `${Math.abs(length) * scale}px` };
	// a start line runs out of the block's start edge; a centre line from its middle toward the container's
	const anchor =
		from === "center"
			? { [startProperty(horizontal, length > 0)]: "50%" }
			: { [startProperty(horizontal, from === "start")]: "100%" };
	return {
		key,
		horizontal,
		style: { ...across, ...size, ...anchor },
		label: `${Math.round(Math.abs(length))}`,
	};
}

// the property that puts a line on the start side of its anchor
function startProperty(horizontal: boolean, towardStart: boolean) {
	if (horizontal) return towardStart ? "right" : "left";
	return towardStart ? "bottom" : "top";
}
</script>
