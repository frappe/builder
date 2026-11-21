<template>
	<div
		v-for="line in lines"
		:key="line.key"
		class="pointer-events-none absolute border-dashed border-blue-400"
		:class="line.horizontal ? 'h-0 border-t' : 'w-0 border-l'"
		:style="line.style">
		<span
			class="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 whitespace-nowrap rounded-[3px] bg-blue-500 px-1 py-0.5 text-[10px] leading-none text-white">
			{{ line.label }}
		</span>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import BlockPosition from "@/utils/blockPosition";
import { PIN_PROPERTIES, type AxisBox, type BlockPins, type Box, type Edge } from "@/utils/positionPins";
import { getElementRotation } from "@/utils/rotation";
import { inject, nextTick, ref, watch, type CSSProperties } from "vue";

type PinLine = { key: string; horizontal: boolean; style: CSSProperties; label: string };

const props = defineProps<{
	block: Block;
	target: HTMLElement | SVGElement;
}>();

const canvasProps = inject("canvasProps") as CanvasProps;
const lines = ref<PinLine[]>([]);

// a dashed line from each pinned edge to its containing block, or from a centred block's
// centre to the container's, drawn around the selection box
const measure = () => {
	const position = new BlockPosition(props.block, props.target);
	// insets ignore rotation, so a rotated block's lines would point the wrong way
	const box = getElementRotation(props.target) ? null : position.measure();
	lines.value = box ? pinLines(position.pins, box, canvasProps.scale) : [];
};

watch(
	() => [
		PIN_PROPERTIES.map((property) => props.block.getStyle(property as styleProperty)),
		props.block.getParentBlock()?.getStyle("width"),
		props.block.getParentBlock()?.getStyle("height"),
		canvasProps.scale,
	],
	() => nextTick(measure),
	{ immediate: true, deep: true },
);

function pinLines(pins: BlockPins, box: Box, scale: number) {
	return [...axisLines(pins, box.x, scale, true), ...axisLines(pins, box.y, scale, false)];
}

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
