<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			:propertyKey="type"
			:component="SplitModeInput"
			:label="label"
			:unitOptions="UNITS"
			defaultUnit="px"
			:enableStates="true"
			:enableSlider="true"
			:split="!linked"
			:uniformTitle="`Use uniform ${type}`"
			:splitTitle="`Use individual ${type} sides`"
			:labels="SIDE_LABELS"
			:splitValue="splitValue"
			:combineValues="combine"
			:normalizeValue="normalize"
			:inputAttrs="type === 'margin' ? {} : { min: 0 }"
			:getModelValue="() => readValue(null)"
			:getPlaceholder="getPlaceholder"
			:setModelValue="applyValue"
			:getVariantValue="readValue"
			:setVariantValue="setVariantValue"
			@update:split="setSplitMode" />
	</div>
</template>

<script lang="ts" setup>
import SplitModeInput from "@/components/Controls/SplitModeInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { useSplitBoxControl } from "@/utils/useSplitBoxControl";
import { computed } from "vue";

type SpacingType = "margin" | "padding";
type BoxValue = string | number | boolean | null;

const UNITS = ["px", "em", "rem"];
const SIDE_LABELS = ["T", "R", "B", "L"];

const props = defineProps<{ type: SpacingType }>();

const label = computed(() => (props.type === "margin" ? "Margin" : "Padding"));

const getBaseValue = (cascading = false) =>
	props.type === "margin"
		? blockController.getMargin({ nativeOnly: !cascading, cascading })
		: blockController.getPadding({ nativeOnly: !cascading, cascading });

const readValue = (state: string | null) =>
	state ? String(blockController.getNativeStyle(`${state}:${props.type}`) ?? "") : String(getBaseValue());

const getPlaceholder = () => String(getBaseValue(true));

const writeValue = (state: string | null, value: BoxValue) => {
	if (state) blockController.setStyle(`${state}:${props.type}`, value);
	else if (props.type === "margin") blockController.setMargin(String(value || ""));
	else blockController.setPadding(String(value || ""));
};

const { linked, applyValue, splitValue, normalize, combine, setSplitMode, setVariantValue } =
	useSplitBoxControl({ defaultUnit: UNITS[0], readValue, writeValue });
</script>
