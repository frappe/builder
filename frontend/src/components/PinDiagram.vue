<template>
	<div class="relative size-20 shrink-0 rounded-[10px] bg-surface-gray-2">
		<div class="absolute inset-6 rounded-[4px] border border-outline-gray-2 bg-surface-base" />
		<Tooltip v-for="control in controls" :key="control.key" :text="control.tooltip" :hoverDelay="300">
			<button
				type="button"
				class="group absolute flex items-center justify-center rounded-[4px] outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
				:class="[control.area, { 'cursor-not-allowed': control.disabled }]"
				:aria-label="control.tooltip"
				:aria-pressed="control.pressed"
				:aria-disabled="control.disabled"
				@click="!control.disabled && control.toggle()">
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
import { SIDE_PINS, type Axis, type BlockPins, type Side } from "@/utils/positionPins";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{
	pins: BlockPins;
}>();

const emit = defineEmits<{
	toggle: [side: Side];
	toggleCenter: [axes: Axis[]];
}>();

// the diagram is 80px, with the block drawn as the 32px box in its middle
const EDGES = [
	{ side: "top", area: "left-[30px] top-0 h-6 w-5", line: "h-3.5 w-0.5" },
	{ side: "right", area: "right-0 top-[30px] h-5 w-6", line: "h-0.5 w-3.5" },
	{ side: "bottom", area: "bottom-0 left-[30px] h-6 w-5", line: "h-3.5 w-0.5" },
	{ side: "left", area: "left-0 top-[30px] h-5 w-6", line: "h-0.5 w-3.5" },
] as const;

// each line of the plus takes the two triangles of the box nearest to it; the dot where
// they cross centres both
const CENTERS: { axes: Axis[]; area: string; line: string; tooltip: string }[] = [
	{
		axes: ["x"],
		area: "inset-6 [clip-path:polygon(0_0,100%_0,50%_50%,100%_100%,0_100%,50%_50%)]",
		line: "h-5 w-0.5",
		tooltip: __("Center horizontally"),
	},
	{
		axes: ["y"],
		area: "inset-6 [clip-path:polygon(0_0,50%_50%,100%_0,100%_100%,50%_50%,0_100%)]",
		line: "h-0.5 w-5",
		tooltip: __("Center vertically"),
	},
	{ axes: ["x", "y"], area: "left-[33px] top-[33px] size-3.5", line: "size-1.5", tooltip: __("Center") },
];

const SIDE_NAMES = { top: __("top"), right: __("right"), bottom: __("bottom"), left: __("left") };

const controls = computed(() => [
	...EDGES.map(({ side, area, line }) => {
		const [axis, edge] = SIDE_PINS[side];
		const pressed = props.pins.isPinned(side);
		// the last pin on an axis stays; pinning the other side first moves it there
		const last = props.pins.axis(axis).pin === edge;
		return {
			key: side,
			area,
			line,
			pressed,
			disabled: last,
			tooltip: !pressed
				? __("Pin to {0}", [SIDE_NAMES[side]])
				: last
					? __("Pinned to {0}", [SIDE_NAMES[side]])
					: __("Unpin {0}", [SIDE_NAMES[side]]),
			toggle: () => emit("toggle", side),
		};
	}),
	...CENTERS.map(({ axes, area, line, tooltip }) => ({
		key: axes.join(""),
		area,
		line,
		pressed: axes.every((axis) => props.pins.axis(axis).pin === "center"),
		disabled: props.pins.custom,
		tooltip: props.pins.custom
			? __("Centering is off while the block has its own translate or transform")
			: tooltip,
		toggle: () => emit("toggleCenter", axes),
	})),
]);
</script>
