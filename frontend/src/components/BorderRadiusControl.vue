<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			propertyKey="borderRadius"
			:component="SplitModeInput"
			label="Radius"
			:unitOptions="['px', '%']"
			defaultUnit="px"
			:enableStates="true"
			uniformTitle="Use uniform radius"
			splitTitle="Use individual corner radii"
			:labels="SPLIT_LABELS"
			:splitValue="splitValue"
			:combineValues="combine"
			:normalizeValue="normalize"
			:inputAttrs="{ min: 0 }"
			placeholder="None"
			:getModelValue="() => readValue(null)"
			:getVariantValue="readValue"
			:getControlAttrs="getControlAttrs" />
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

const splitValue = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");
const combine = (parts: BoxValue[]) => parts.join(" ");

const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		split: splitModes[key] ?? new Set(splitValue(readValue(variant))).size > 1,
		"onUpdate:split": (split: boolean) => (splitModes[key] = split),
	};
};
</script>
