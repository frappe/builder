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
			:labels="SPLIT_LABELS"
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
import { expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { RADIUS_UNIT_OPTIONS } from "@/utils/unitOptions";
import { reactive } from "vue";

type BoxValue = string | number | boolean | null;

const SPLIT_LABELS = ["TL", "TR", "BR", "BL"];

const splitModes = reactive<Record<string, boolean>>({});

const readValue = (state: string | null = null) =>
	String(blockController.getStyle(state ? `${state}:borderRadius` : "borderRadius") || "");

const ensureRoundedContentIsClipped = (value: BoxValue) => {
	if (!value) return;
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};

const toControlValues = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");
const toModelValue = (parts: BoxValue[]) => parts.join(" ");
const getMergedValue = (parts: BoxValue[]) => parts[0] ?? "0px";
const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		enableSlider: true,
		split: new Set(toControlValues(readValue(variant))).size > 1 || (splitModes[key] ?? false),
		"onUpdate:split": (split: boolean) => (splitModes[key] = split),
	};
};
</script>
