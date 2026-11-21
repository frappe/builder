<template>
	<StylePropertyControl
		:component="Autocomplete"
		:propertyKey="property"
		:label="label"
		:enableSlider="true"
		:getPlaceholder="stretchedAxis ? getPlaceholder : undefined"
		:setModelValue="stretchedAxis ? setModelValue : undefined"
		:options="options"
		:unitOptions="DIMENSION_UNIT_OPTIONS"></StylePropertyControl>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import BlockPosition from "@/utils/blockPosition";
import { DIMENSION_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed } from "vue";

const props = defineProps<{
	property: string;
	label: string;
}>();

// a free block pinned to both sides of this axis gets its size from them
const stretchedAxis = computed(() => {
	const axis = ({ width: "x", height: "y" } as const)[props.property as "width" | "height"];
	if (!axis || !blockController.isBlockSelected() || blockController.multipleBlocksSelected()) return null;
	const block = blockController.getFirstSelectedBlock();
	if (!block.isMovable()) return null;
	return new BlockPosition(block, null).pins.axis(axis).pin === "stretch" ? axis : null;
});

// a stretched axis already fills the space between its pins, so 100% is left out
const options = computed(() => [
	{ label: __("Auto"), value: "auto" },
	{ label: __("Fit Content"), value: "fit-content" },
	...(stretchedAxis.value ? [] : [{ label: __("Stretch"), value: "100%" }]),
]);

const getPlaceholder = () => __("Set by pins");

// a size typed in keeps the start pin, so it never fights the end pin; auto is what the
// stretch already uses
const setModelValue = (value: string | number | boolean) => {
	if (value && value !== "auto" && stretchedAxis.value) {
		new BlockPosition(blockController.getFirstSelectedBlock(), null).releaseStretch(stretchedAxis.value);
	}
	blockController.setStyle(props.property, value);
};
</script>
