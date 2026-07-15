<template>
	<div class="flex w-full flex-col gap-2">
		<StylePropertyControl
			propertyKey="borderRadius"
			:component="SplitModeInput"
			label="Radius"
			:unitOptions="['px', '%']"
			defaultUnit="px"
			:enableStates="true"
			:split="!linked"
			uniformTitle="Use uniform radius"
			splitTitle="Use individual corner radii"
			:labels="CORNER_LABELS"
			:splitValue="splitValue"
			:combineValues="combine"
			:normalizeValue="normalize"
			:inputAttrs="{ min: 0 }"
			placeholder="None"
			:getModelValue="() => readValue(null)"
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

type BoxValue = string | number | boolean | null;

const CORNER_LABELS = ["TL", "TR", "BR", "BL"];

const readValue = (state: string | null) =>
	String(blockController.getStyle(state ? `${state}:borderRadius` : "borderRadius") || "");

const ensureRoundedContentIsClipped = () => {
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};

const writeValue = (state: string | null, value: BoxValue) => {
	blockController.setStyle(state ? `${state}:borderRadius` : "borderRadius", value);
	if (value) ensureRoundedContentIsClipped();
};

const { linked, applyValue, splitValue, normalize, combine, setSplitMode, setVariantValue } =
	useSplitBoxControl({ defaultUnit: "px", readValue, writeValue });
</script>
