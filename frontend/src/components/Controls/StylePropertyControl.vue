<template>
	<BasePropertyControl
		v-bind="baseProps"
		:variants="allVariants"
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
		styleProperty: string;
		label?: string;
		placeholder?: string;
		getModelValue?: () => string;
		getPlaceholder?: () => string;
		setModelValue?: (value: string) => void;
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
		enableStates?: boolean;
		enabledStates?: string[];
		variants?: Array<{ name: string; property: string; label: string }>;
	}>(),
	{
		enableStates: true,
		enabledStates: () => ["hover", "active", "focus"],
		variants: () => [],
	},
);

const stateLabels: Record<string, string> = {
	hover: "On Hover",
	active: "On Active",
	focus: "On Focus",
};

const stateVariants = computed(() =>
	props.enabledStates.map((state) => ({
		name: state,
		property: `${state}:${props.styleProperty}`,
		label: stateLabels[state] || state,
	})),
);

const allVariants = computed(() => [
	...(props.enableStates ? stateVariants.value : []),
	...(props.variants || []),
]);

const getVariantValue = (variantName: string): string => {
	if (stateVariants.value.find((v) => v.name === variantName)) {
		return String(blockController.getNativeStyle(`${variantName}:${props.styleProperty}`) || "");
	}
	const property = props.variants?.find((v) => v.name === variantName)?.property;
	return property ? String(blockController.getAttribute(property) || "") : "";
};

const setVariantValue = (variantName: string, value: string | null) => {
	if (stateVariants.value.find((v) => v.name === variantName)) {
		if (value !== null) {
			blockController.getSelectedBlocks().forEach((block) => {
				if (!block.getStyle("transitionDuration")) {
					block.setStyle("transitionDuration", "300ms");
					block.setStyle("transitionTimingFunction", "ease");
					block.setStyle("transitionProperty", "all");
				}
			});
		}
		blockController.setStyle(`${variantName}:${props.styleProperty}`, value);
		return;
	}
	const property = props.variants?.find((v) => v.name === variantName)?.property;
	if (property) blockController.setAttribute(property, value || "");
};

const baseProps = computed(() => {
	const { enableStates, enabledStates, variants, ...rest } = props;
	return {
		...rest,
		controlType: "style" as const,
		getModelValue:
			props.getModelValue || (() => String(blockController.getNativeStyle(props.styleProperty) ?? "")),
		setModelValue:
			props.setModelValue || ((value: string) => blockController.setStyle(props.styleProperty, value)),
		getPlaceholder:
			props.getPlaceholder ||
			(() => String(blockController.getCascadingStyle(props.styleProperty) ?? "unset")),
	};
});
</script>
