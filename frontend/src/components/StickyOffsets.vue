<template>
	<div class="flex w-full flex-col gap-3">
		<OptionToggle
			:options="[
				{ label: __('Top'), value: 'top' },
				{ label: __('Bottom'), value: 'bottom' },
				{ label: __('Both'), value: 'both' },
			]"
			:modelValue="edges"
			@update:modelValue="setEdges" />
		<InlineInput
			v-for="side in shownSides"
			:key="side"
			:label="side === 'top' ? __('Top offset') : __('Bottom offset')"
			:unitOptions="POSITION_UNIT_OPTIONS"
			:modelValue="fieldValue(side)"
			:placeholder="String(read(side) || '0px')"
			@update:modelValue="(value: string | null) => position().apply({ [side]: value || '0px' })" />
		<p class="text-p-xs text-ink-gray-5">
			{{
				__(
					"Scrolls with the page, then sticks this far from the window edge while its parent is in view. Needs a parent taller than itself.",
				)
			}}
		</p>
	</div>
</template>
<script setup lang="ts">
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import { __ } from "@/translation";
import blockController from "@/utils/blockController";
import BlockPosition from "@/utils/blockPosition";
import type { StylePatch } from "@/utils/positionPins";
import { isSet, readSide } from "@/utils/positionValues";
import { POSITION_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed } from "vue";

type StickySide = "top" | "bottom";

const block = computed(() => blockController.getFirstSelectedBlock());
const position = () => new BlockPosition(block.value, null);

const read = (side: StickySide) =>
	readSide((property) => block.value.getActiveStyleValue(property as styleProperty), side);
const isStuck = (side: StickySide) => isSet(read(side));

// a sticky block with neither offset does not stick, so no edge reads as on
const edges = computed(() => {
	if (isStuck("top") && isStuck("bottom")) return "both";
	return isStuck("bottom") ? "bottom" : isStuck("top") ? "top" : "";
});

const shownSides = computed(
	() => (edges.value === "both" ? ["top", "bottom"] : [edges.value || "top"]) as StickySide[],
);

const fieldValue = (side: StickySide) => {
	const own = block.value.getStyle(block.value.getActiveStyleProperty(side), null, true);
	return isSet(own) ? String(own) : "";
};

// moving to the other edge takes the offset along
const setEdges = (value: string | number | boolean) => {
	const offset = String(read(edges.value === "bottom" ? "bottom" : "top") || "0px");
	const patch: StylePatch = {};
	(["top", "bottom"] as StickySide[]).forEach((side) => {
		const stick = value === side || value === "both";
		if (stick !== isStuck(side)) patch[side] = stick ? offset : null;
	});
	position().apply(patch);
};
</script>
