<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			:propertyKey="type"
			:component="SplitModeInput"
			:label="label"
			:unitOptions="BOX_UNIT_OPTIONS"
			:enableStates="true"
			:enableSlider="enableSlider"
			:splits="SPLITS"
			:toControlValues
			:toModelValue
			:normalizeValue="normalize"
			:inputAttrs="type === 'margin' ? {} : { min: 0 }"
			:getModelValue="readValue"
			:getPlaceholder="getPlaceholder"
			:getVariantValue="readValue"
			:getMergedValue
			:setModelValue
			:getControlAttrs="getControlAttrs" />
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { collapseBoxShorthand, expandBoxShorthand, normalizeValueWithUnits } from "@/utils/cssUtils";
import { BOX_UNIT_OPTIONS } from "@/utils/unitOptions";
import { computed, ref, watch } from "vue";

type SpacingType = "margin" | "padding";
type BoxValue = string | number | boolean | null;

const SPLITS = ["T", "R", "B", "L"];
const enableSlider = true;

const props = defineProps<{ type: SpacingType }>();
const splitModes = ref<Record<string, boolean>>({});

watch(
	() => blockController.getSelectedBlocks(),
	() => (splitModes.value = {}),
);

const label = computed(() => (props.type === "margin" ? "Margin" : "Padding"));

const getBaseValue = (cascading = false) =>
	props.type === "margin"
		? blockController.getMargin({ nativeOnly: !cascading, cascading })
		: blockController.getPadding({ nativeOnly: !cascading, cascading });

const readValue = (state: string | null = null) =>
	state ? String(blockController.getNativeStyle(`${state}:${props.type}`) ?? "") : String(getBaseValue());

const getPlaceholder = () => String(getBaseValue(true));

const toControlValues = (value: unknown) => expandBoxShorthand(value);
const normalize = (value: BoxValue) => normalizeValueWithUnits(String(value || "0"), "px");
const toModelValue = (parts: BoxValue[]) => collapseBoxShorthand(parts);
const getMergedValue = (parts: BoxValue[]) => parts[0] ?? 0;
const getControlAttrs = (variant: string | null) => {
	const key = variant ?? "main";
	return {
		split: new Set(toControlValues(readValue(variant))).size > 1 || (splitModes.value[key] ?? false),
		enableSlider,
		"onUpdate:split": (split: boolean) => (splitModes.value[key] = split),
	};
};

const setModelValue = (val: string | boolean | number) => {
	if (typeof val == "boolean") return;
	if (props.type == "margin") blockController.setMargin(String(val));
	else if (props.type == "padding") blockController.setPadding(String(val));
};
</script>
