<template>
	<div class="flex w-full flex-col gap-2">
		<SplitPropertyControl
			:propertyKey="type"
			:label="label"
			:splits="SPLITS"
			:inputAttrs="type === 'margin' ? {} : { min: 0 }"
			:getModelValue="readValue"
			:getPlaceholder
			:getMergedValue
			:setModelValue />
	</div>
</template>

<script lang="ts" setup>
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

type SpacingType = "margin" | "padding";

const SPLITS = ["T", "R", "B", "L"];

const props = defineProps<{ type: SpacingType }>();


const label = computed(() => (props.type === "margin" ? "Margin" : "Padding"));

const getBaseValue = (cascading = false) =>
	props.type === "margin"
		? blockController.getMargin({ nativeOnly: !cascading, cascading })
		: blockController.getPadding({ nativeOnly: !cascading, cascading });

const readValue = (state: string | null = null) =>
	state ? String(blockController.getNativeStyle(`${state}:${props.type}`) ?? "") : String(getBaseValue());

const getPlaceholder = () => String(getBaseValue(true));

const getMergedValue = (parts: StyleValue[]) => parts[0] ?? 0;

const setModelValue = (val: string | boolean | number) => {
	if (typeof val == "boolean") return;
	if (props.type == "margin") blockController.setMargin(String(val));
	else if (props.type == "padding") blockController.setPadding(String(val));
};
</script>
