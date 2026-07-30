<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			label="Radius"
			placeholder="None"
			propertyKey="borderRadius"
			:component="SplitModeInput"
			:unitOptions="RADIUS_UNIT_OPTIONS"
			:enableStates="true"
			:enableSlider="true"
			:splits="SPLITS"
			:toControlValues
			:toModelValue
			:normalizeValue="normalize"
			:inputAttrs="{ min: 0 }"
			:getModelValue="readValue"
			:getVariantValue="readValue"
			:getControlAttrs="getControlAttrs"
			:getMergedValue
			@update:modelValue="ensureRoundedContentIsClipped" />
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { collapseBoxShorthand, expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { RADIUS_UNIT_OPTIONS } from "@/utils/unitOptions";
import { useSplitControl, type SplitValue } from "@/composables/useSplitControl";

const SPLITS = ["TL", "TR", "BR", "BL"];

const readValue = (state: string | null = null) =>
	String(blockController.getStyle(state ? `${state}:borderRadius` : "borderRadius") || "");

const ensureRoundedContentIsClipped = (value: SplitValue) => {
	if (!value) return;
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};

const toControlValues = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: SplitValue) => normalizeValueWithUnits(String(value || "0"), "px");
const toModelValue = (parts: SplitValue[]) => collapseBoxShorthand(parts);
const { getControlAttrs, getMergedValue } = useSplitControl(toControlValues, readValue);
</script>
