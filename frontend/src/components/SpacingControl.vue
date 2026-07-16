<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			:propertyKey="type"
			:component="SplitModeInput"
			:label="label"
			:unitOptions="UNITS"
			defaultUnit="px"
			:enableStates="true"
			:enableSlider="enableSlider"
			:uniformTitle="`Use uniform ${type}`"
			:splitTitle="`Use individual ${type} sides`"
			:labels="SPLIT_LABELS"
			:splitValue="splitValue"
			:combineValues="combine"
			:normalizeValue="normalize"
			:inputAttrs="type === 'margin' ? {} : { min: 0 }"
			:getModelValue="() => readValue(null)"
			:getPlaceholder="getPlaceholder"
			:getVariantValue="readValue"
			:getMergedValue
			:getControlAttrs="getControlAttrs" />
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { computed, reactive } from "vue";

type SpacingType = "margin" | "padding";
type BoxValue = string | number | boolean | null;

const UNITS = ["px", "em", "rem"];
const SPLIT_LABELS = ["T", "R", "B", "L"];
const enableSlider = true;

const props = defineProps<{ type: SpacingType }>();
const splitModes = reactive<Record<string, boolean>>({});

const label = computed(() => (props.type === "margin" ? "Margin" : "Padding"));

const getBaseValue = (cascading = false) =>
	props.type === "margin"
		? blockController.getMargin({ nativeOnly: !cascading, cascading })
		: blockController.getPadding({ nativeOnly: !cascading, cascading });

const readValue = (state: string | null) =>
	state ? String(blockController.getNativeStyle(`${state}:${props.type}`) ?? "") : String(getBaseValue());

const getPlaceholder = () => String(getBaseValue(true));

const splitValue = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");
const combine = (parts: BoxValue[]) => parts.join(" ");
const getMergedValue = (parts: any[]) => 0;
const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		split: splitModes[key] ?? new Set(splitValue(readValue(variant))).size > 1,
		enableSlider,
		"onUpdate:split": (split: boolean) => (splitModes[key] = split),
	};
};
</script>
