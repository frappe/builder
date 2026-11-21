<template>
	<div class="flex w-full flex-col items-center gap-5">
		<StylePropertyControl
			propertyKey="position"
			type="select"
			:getModelValue="() => position"
			:setModelValue="setPosition"
			defaultValue="static"
			:enableStates="false"
			:options="[
				{ label: __('Auto'), value: 'static' },
				{ label: __('Free'), value: 'absolute' },
				{ label: __('Relative'), value: 'relative' },
				{
					label: __('Fixed'),
					value: 'fixed',
				},
				{ label: __('Sticky'), value: 'sticky' },
			]"></StylePropertyControl>
		<div class="grid w-full grid-cols-[1fr_auto_1fr] items-center gap-2" v-if="showHandler">
			<InlineInput
				v-for="side in SIDES"
				:key="`${side}-${refusals[side]}`"
				:class="SIDE_CELLS[side]"
				:placeholder="placeholder(side)"
				:unitOptions="POSITION_UNIT_OPTIONS"
				:hideClearButton="true"
				:modelValue="sideValue(side)"
				@update:modelValue="(value: string) => setSide(side, value)" />
			<PinDiagram
				v-if="free"
				class="col-start-2 row-start-2"
				:pins="pins"
				@toggle="(side: Side) => blockPosition().toggle(side)"
				@toggleCenter="(axes: Axis[]) => blockPosition().toggleCenter(axes)" />
		</div>
	</div>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import InlineInput from "@/components/Controls/InlineInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import PinDiagram from "@/components/PinDiagram.vue";
import blockController from "@/utils/blockController";
import BlockPosition from "@/utils/blockPosition";
import type { Axis, Side } from "@/utils/positionPins";
import { POSITION_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed, reactive, watch } from "vue";

const position = computed({
	get() {
		const pos = (blockController.getStyle("position") as string) || "static";
		return pos;
	},
	set(value: string) {
		if (
			value === "static" &&
			(blockController.getCascadingStyle("position") === "static" ||
				!blockController.getCascadingStyle("position"))
		) {
			value = "";
		}
		blockController.setStyle("position", value);
		const parentBlock = blockController.getParentBlock();
		if (parentBlock) {
			parentBlock.setStyle("position", "relative");
		}
	},
});

const setPosition = (val: string | number | boolean) => {
	if (typeof val === "string") {
		if (free.value && !["absolute", "fixed"].includes(val)) blockPosition(null).dropCentering();
		position.value = val;
	}
};

watch(position, (value) => {
	if (value === "static") {
		blockController.setStyle("top", "");
		blockController.setStyle("left", "");
		blockController.setStyle("right", "");
		blockController.setStyle("bottom", "");
	}
});

const showHandler = computed(() => {
	return ["absolute", "fixed", "sticky"].includes(position.value);
});

const SIDES: Side[] = ["top", "right", "bottom", "left"];
const SIDE_CELLS = {
	top: "col-start-2 row-start-1 w-20 justify-self-center",
	right: "col-start-3 row-start-2",
	bottom: "col-start-2 row-start-3 w-20 justify-self-center",
	left: "col-start-1 row-start-2",
};
const SIDE_LABELS = { top: __("Top"), right: __("Right"), bottom: __("Bottom"), left: __("Left") };

// a Free or Fixed block is placed by its pins; a sticky one only says how far it sticks
const free = computed(() => ["absolute", "fixed"].includes(position.value));
const block = () => blockController.getFirstSelectedBlock();
// without an element, for edits that don't measure
const blockPosition = (element?: null) => new BlockPosition(block(), element);
const pins = computed(() => blockPosition(null).pins);
// bumped when a side's edit is refused, so its field shows the value again
const refusals = reactive({ top: 0, right: 0, bottom: 0, left: 0 });

// a pin shows the value it reads in the active state; an unpinned side reads auto, and the
// sides of a centred axis center
const sideValue = (side: Side) => {
	if (!free.value) return blockController.getStyle(side) as string;
	return pins.value.isPinned(side) ? (block().getActiveStyleValue(side) as string) : "";
};

const placeholder = (side: Side) => {
	if (!free.value) return SIDE_LABELS[side];
	return pins.value.axis(side === "left" || side === "right" ? "x" : "y").pin === "center"
		? __("center")
		: __("auto");
};

const setSide = (side: Side, value: string) => {
	if (!free.value) return blockController.setStyle(side, value);
	if (!blockPosition().setSide(side, value || null)) refusals[side]++;
};
</script>
