<template>
	<div class="flex w-full flex-col gap-3">
		<!-- Border Color -->
		<StylePropertyControl
			label="Border Color"
			propertyKey="borderColor"
			:component="ColorInput"
			:popoverOffset="120"
			:events="colorEvents" />

		<!-- Border Width (with Split Mode Input) -->
		<SplitPropertyControl
			v-if="hasColor"
			label="Border Width"
			propertyKey="borderWidth"
			:unitOptions="BORDER_UNIT_OPTIONS"
			:splits="SPLITS"
			:toModelValue="toModelValue"
			:getModelValue="readValue" />

		<!-- Border Style -->
		<StylePropertyControl
			v-if="hasColor"
			label="Border Style"
			propertyKey="borderStyle"
			type="select"
			:options="[
				{ value: 'solid', label: 'Solid' },
				{ value: 'dashed', label: 'Dashed' },
				{ value: 'dotted', label: 'Dotted' },
			]" />
	</div>
</template>

<script lang="ts" setup>
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import blockController from "@/utils/blockController";
import { BORDER_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed } from "vue";

const SPLITS = ["T", "R", "B", "L"];


const readValue = (state: string | null = null) => {
	const key = state ? `${state}:borderWidth` : "borderWidth";
	return String(blockController.getStyle(key) || "");
};

const toModelValue = (parts: StyleValue[]) => parts.join(" ");

const hasColor = computed(() => {
	return Boolean(
		blockController.getStyle("borderColor") ||
		blockController.getStyle("borderWidth")
	);
});

const colorEvents = {
	"update:modelValue": (val: any) => {
		if (val) {
			if (!blockController.getStyle("borderWidth")) {
				blockController.setStyle("borderWidth", "1px");
				blockController.setStyle("borderStyle", "solid");
			}
		} else {
			blockController.setStyle("borderWidth", null);
			blockController.setStyle("borderStyle", null);
		}
	}
};
</script>
