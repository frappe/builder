<template>
	<div class="relative size-20 shrink-0 rounded-[10px] bg-surface-gray-2">
		<div
			class="absolute inset-6 rounded-[4px] border border-outline-gray-2 bg-surface-base"
			aria-hidden="true" />
		<Tooltip v-for="control in controls" :key="control.key" :text="control.tooltip" :hoverDelay="300">
			<button
				type="button"
				class="group absolute flex items-center justify-center rounded-[4px] outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				:class="[control.area, { 'cursor-not-allowed': control.disabled }]"
				:aria-label="control.tooltip"
				:aria-pressed="control.pressed"
				:aria-disabled="control.disabled"
				@click="control.toggle">
				<span
					class="rounded-full transition-colors"
					:class="[
						control.line,
						control.pressed
							? 'bg-surface-gray-8'
							: control.disabled
								? 'bg-surface-gray-3'
								: 'bg-surface-gray-4 group-hover:bg-surface-gray-6',
					]" />
			</button>
		</Tooltip>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import type { Axis, BlockPins } from "@/utils/positionPins";
import type { Side } from "@/utils/positionValues";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	pins: BlockPins;
}>();

const emit = defineEmits<{
	toggle: [side: Side];
	toggleCenter: [axis: Axis];
}>();

// the diagram is 80px with the block drawn as the 32px box in its middle
const EDGES = [
	{ side: "top", area: "left-[30px] top-0 h-6 w-5", line: "h-3.5 w-0.5" },
	{ side: "right", area: "right-0 top-[30px] h-5 w-6", line: "h-0.5 w-3.5" },
	{ side: "bottom", area: "bottom-0 left-[30px] h-6 w-5", line: "h-3.5 w-0.5" },
	{ side: "left", area: "left-0 top-[30px] h-5 w-6", line: "h-0.5 w-3.5" },
] as const;

// both centre lines cross the 32px box, so each takes the two triangles nearest to it
const CENTERS = [
	{
		axis: "x",
		area: "inset-6 [clip-path:polygon(0_0,100%_0,50%_50%,100%_100%,0_100%,50%_50%)]",
		line: "h-5 w-0.5",
	},
	{
		axis: "y",
		area: "inset-6 [clip-path:polygon(0_0,50%_50%,100%_0,100%_100%,50%_50%,0_100%)]",
		line: "h-0.5 w-5",
	},
] as const;

const EDGE_TOOLTIPS = {
	top: [__("Pin to top"), __("Pinned to top. Click to unpin")],
	right: [__("Pin to right"), __("Pinned to right. Click to unpin")],
	bottom: [__("Pin to bottom"), __("Pinned to bottom. Click to unpin")],
	left: [__("Pin to left"), __("Pinned to left. Click to unpin")],
};

const CENTER_TOOLTIPS = {
	x: [__("Center horizontally"), __("Centered horizontally. Click to pin to left")],
	y: [__("Center vertically"), __("Centered vertically. Click to pin to top")],
};

const controls = computed(() => [
	...EDGES.map(({ side, area, line }) => {
		const axis = side === "left" || side === "right" ? "x" : "y";
		const pressed = props.pins.axis(axis).isPinned(side === "left" || side === "top" ? "start" : "end");
		return {
			key: side,
			area,
			line,
			pressed,
			disabled: false,
			tooltip: EDGE_TOOLTIPS[side][pressed ? 1 : 0],
			toggle: () => emit("toggle", side),
		};
	}),
	...CENTERS.map(({ axis, area, line }) => {
		const pressed = props.pins.axis(axis).pin === "center";
		return {
			key: `center-${axis}`,
			area,
			line,
			pressed,
			disabled: props.pins.custom,
			tooltip: props.pins.custom
				? __("Centering is off while the block has its own translate or transform")
				: CENTER_TOOLTIPS[axis][pressed ? 1 : 0],
			// aria-disabled rather than disabled, so the tooltip still says why
			toggle: () => !props.pins.custom && emit("toggleCenter", axis),
		};
	}),
]);
</script>
