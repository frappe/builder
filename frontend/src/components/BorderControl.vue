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
		<StylePropertyControl
			v-if="hasColor"
			label="Border Width"
			propertyKey="borderWidth"
			:component="SplitModeInput"
			:unitOptions="BORDER_UNIT_OPTIONS"
			:enableStates="true"
			:enableSlider="true"
			:splits="SPLITS"
			:toControlValues="toControlValues"
			:toModelValue="toModelValue"
			:normalizeValue="normalize"
			:inputAttrs="{ min: 0 }"
			:getModelValue="readValue"
			:getVariantValue="readValue"
			:getControlAttrs="getControlAttrs"
			:getMergedValue="getMergedValue" />

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
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import blockController from "@/utils/blockController";
import { expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { BORDER_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed, ref, watch } from "vue";

type BoxValue = string | number | boolean | null;

const SPLITS = ["T", "R", "B", "L"];
const splitModes = ref<Record<string, boolean>>({});

// Reset split modes on selection change
watch(
	() => blockController.getSelectedBlocks(),
	() => {
		splitModes.value = {};
	}
);

const readValue = (state: string | null = null) => {
	const key = state ? `${state}:borderWidth` : "borderWidth";
	return String(blockController.getStyle(key) || "");
};

const toControlValues = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");
const toModelValue = (parts: BoxValue[]) => parts.join(" ");
const getMergedValue = (parts: BoxValue[]) => parts[0] ?? "0px";

const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		split: new Set(toControlValues(readValue(variant))).size > 1 || (splitModes.value[key] ?? false),
		enableSlider: true,
		"onUpdate:split": (split: boolean) => (splitModes.value[key] = split),
	};
};

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
