<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			label="Radius"
			placeholder="None"
			propertyKey="borderRadius"
			uniformTitle="Use uniform radius"
			splitTitle="Use individual corner radii"
			defaultUnit="px"
			:component="SplitModeInput"
			:unitOptions="['px', '%']"
			:enableStates="true"
			:labels="SPLIT_LABELS"
			:splitValue="splitValue"
			:combineValues="combine"
			:normalizeValue="normalize"
			:inputAttrs="{ min: 0 }"
			:getModelValue="() => readValue(null)"
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
import { reactive } from "vue";

type BoxValue = string | number | boolean | null;

const SPLIT_LABELS = ["TL", "TR", "BR", "BL"];

const splitModes = reactive<Record<string, boolean>>({});

const readValue = (state: string | null) =>
	String(blockController.getStyle(state ? `${state}:borderRadius` : "borderRadius") || "");

const ensureRoundedContentIsClipped = (value: BoxValue) => {
	if (!value) return;
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};

const splitValue = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");
const combine = (parts: BoxValue[]) => parts.join(" ");
const getMergedValue = (parts: any[]) => "0px";
const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		split: new Set(splitValue(readValue(variant))).size > 1 || (splitModes[key] ?? false),
		"onUpdate:split": (split: boolean) => (splitModes[key] = split),
	};
};
</script>
