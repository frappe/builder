<template>
	<div class="flex w-full flex-col gap-2">
		<SplitPropertyControl
			label="Radius"
			placeholder="None"
			propertyKey="borderRadius"
			:unitOptions="RADIUS_UNIT_OPTIONS"
			:splits="SPLITS"
			:getModelValue="readValue"
			@update:modelValue="ensureRoundedContentIsClipped" />
	</div>
</template>

<script lang="ts" setup>
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import blockController from "@/utils/blockController";
import { RADIUS_UNIT_OPTIONS } from "@/utils/unitOptions";

const SPLITS = ["TL", "TR", "BR", "BL"];

const readValue = (state: string | null = null) =>
	String(blockController.getStyle(state ? `${state}:borderRadius` : "borderRadius") || "");

const ensureRoundedContentIsClipped = (value: StyleValue) => {
	if (!value) return;
	if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
	if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
};
</script>
