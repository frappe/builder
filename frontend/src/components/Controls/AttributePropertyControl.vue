d
<template>
	<BasePropertyControl
		v-bind="baseProps"
		:getVariantValue="getVariantValue"
		:setVariantValue="setVariantValue">
		<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
			<slot :name="name" v-bind="slotData || {}" />
		</template>
	</BasePropertyControl>
</template>

<script lang="ts" setup>
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import blockController from "@/utils/blockController";
import type { Component } from "vue";
import { computed } from "vue";

const props = withDefaults(
	defineProps<{
		propertyKey: string;
		label?: string;
		placeholder?: string;
		getModelValue?: () => string | number | boolean;
		getPlaceholder?: () => string | number | boolean;
		setModelValue?: (value: string | number | boolean) => void;
		enableSlider?: boolean;
		unitOptions?: string[];
		changeFactor?: number;
		minValue?: number;
		maxValue?: number | null;
		component?: Component;
		events?: Record<string, unknown>;
		defaultValue?: string | number;
		allowDynamicValue?: boolean;
		labelPlacement?: "left" | "top";
		variants?: Array<{ name: string; property: string; label: string }>;
	}>(),
	{
		variants: () => [],
	},
);

const baseProps = computed(() => ({
	...props,
	controlType: "attribute" as const,
	getModelValue: props.getModelValue || (() => blockController.getAttribute(props.propertyKey) ?? ""),
	setModelValue:
		props.setModelValue ||
		((value: string | number | boolean) => blockController.setAttribute(props.propertyKey, String(value))),
}));

const getVariantValue = (variantName: string): string | number | boolean => {
	const property = props.variants?.find((v) => v.name === variantName)?.property;
	return property ? (blockController.getAttribute(property) ?? "") : "";
};

const setVariantValue = (variantName: string, value: string | number | boolean | null) => {
	const property = props.variants?.find((v) => v.name === variantName)?.property;
	if (property) blockController.setAttribute(property, value !== null ? String(value) : "");
};
</script>
