<template>
	<div class="flex w-full flex-col gap-3" @mouseenter="measure">
		<div class="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
			<InlineInput
				v-for="side in SIDES"
				:key="side"
				:class="SIDE_CELLS[side]"
				:title="fieldTitle(side)"
				:unitOptions="POSITION_UNIT_OPTIONS"
				:modelValue="fieldValue(side)"
				:placeholder="fieldPlaceholder(side)"
				:hideArrows="true"
				@keydown.capture="(event: KeyboardEvent) => isPinned(side) || ignoreStep(event)"
				@update:modelValue="(value: string | null) => position().setSide(side, value || null)" />
			<PinDiagram
				class="col-start-2 row-start-2"
				:pins="pins"
				@toggle="(side: Side) => position().toggle(axisOf(side), edgeOf(side))"
				@toggleCenter="(axis: Axis) => position().toggleCenter(axis)" />
		</div>
		<div class="flex items-center gap-2">
			<Button
				class="flex-1"
				iconLeft="lucide-maximize"
				:tooltip="__('Pin all four sides at 0 to cover the parent')"
				:disabled="pins.custom"
				@click="position().fill()">
				{{ __("Fill") }}
			</Button>
			<Button
				class="flex-1"
				iconLeft="lucide-crosshair"
				:tooltip="__('Center horizontally and vertically')"
				:disabled="pins.custom"
				@click="position().center()">
				{{ __("Center") }}
			</Button>
		</div>
		<p class="text-p-xs text-ink-gray-5">{{ caption }}</p>
	</div>
</template>
<script setup lang="ts">
import InlineInput from "@/components/Controls/InlineInput.vue";
import PinDiagram from "@/components/PinDiagram.vue";
import { __ } from "@/translation";
import blockController from "@/utils/blockController";
import BlockPosition from "@/utils/blockPosition";
import { axisOf, edgeOf, type Axis, type Box } from "@/utils/positionPins";
import { isSet, readSide, SIDES, type Side } from "@/utils/positionValues";
import { POSITION_UNIT_OPTIONS } from "@/utils/unitOptions";
import { Button } from "frappe-ui";
import { computed, ref } from "vue";

const props = defineProps<{
	fixed: boolean;
}>();

const SIDE_CELLS = {
	top: "col-start-2 row-start-1 w-20 justify-self-center",
	right: "col-start-3 row-start-2",
	bottom: "col-start-2 row-start-3 w-20 justify-self-center",
	left: "col-start-1 row-start-2",
};

const SIDE_NAMES = { top: __("top"), right: __("right"), bottom: __("bottom"), left: __("left") };
const OPPOSITE = { top: "bottom", right: "left", bottom: "top", left: "right" } as const;

const block = computed(() => blockController.getFirstSelectedBlock());
const position = () => new BlockPosition(block.value);
const pins = computed(() => new BlockPosition(block.value, null).pins);
// the block's rendered box, for the field tooltips; measured when the pointer comes in
const box = ref<Box | null>(null);
const measure = () => (box.value = position().measure());

const read = (property: string) => block.value.getActiveStyleValue(property as styleProperty);
const readOwn = (property: string) =>
	block.value.getStyle(block.value.getActiveStyleProperty(property as styleProperty), null, true);

const isPinned = (side: Side) => pins.value.axis(axisOf(side)).isPinned(edgeOf(side));

// an unpinned side has no value to step from, and a step would pin it
const ignoreStep = (event: KeyboardEvent) => {
	if (event.key !== "ArrowUp" && event.key !== "ArrowDown") return;
	event.preventDefault();
	event.stopPropagation();
};

// a pinned side shows the value this breakpoint sets; one it inherits shows as the placeholder
const fieldValue = (side: Side) => {
	const own = readSide(readOwn, side);
	return isPinned(side) && isSet(own) ? String(own) : "";
};

const fieldPlaceholder = (side: Side) => {
	if (pins.value.axis(axisOf(side)).pin === "center") return __("center");
	return isPinned(side) ? String(readSide(read, side)) : __("auto");
};

const fieldTitle = (side: Side) => {
	const distance = shownDistance(side);
	if (isPinned(side)) return pinnedTitle(side);
	if (!distance) return __("Not pinned. Type a value to pin to the {0} edge", [SIDE_NAMES[side]]);
	return __("Not pinned (now {0} from the {1} edge). Type a value to pin it", [distance, SIDE_NAMES[side]]);
};

// clearing the last pin on an axis centres it, or pins the other side
const pinnedTitle = (side: Side) => {
	const axis = pins.value.axis(axisOf(side));
	if (axis.pin === "stretch") return __("Distance from the {0} edge", [SIDE_NAMES[side]]);
	if (axis.toggled(edgeOf(side)) === "center") {
		return __("Distance from the {0} edge. Clear it to center instead", [SIDE_NAMES[side]]);
	}
	return __("Distance from the {0} edge. Clear it to pin the {1} edge instead", [
		SIDE_NAMES[side],
		SIDE_NAMES[OPPOSITE[side]],
	]);
};

// measured from the box as it shows, so a centred block counts its translate
const shownDistance = (side: Side) => {
	const axisBox = box.value?.[axisOf(side)];
	// a fixed block's vertical distances are to the window, which the editor's frame is not
	if (!axisBox || (props.fixed && axisOf(side) === "y")) return "";
	const shift = pins.value.axis(axisOf(side)).pin === "center" ? axisBox.size / 2 : 0;
	const distance = edgeOf(side) === "start" ? axisBox.start - shift : axisBox.end + shift;
	return `${Math.round(distance)}px`;
};

const caption = computed(() => {
	if (pins.value.custom) {
		return __("Also moved by its own translate or transform, which the pins leave alone.");
	}
	if (props.fixed) return __("Pinned to the browser window, so it stays put while the page scrolls.");
	return __("Pinned to its parent. Pin both sides to stretch, or none to center.");
});
</script>
