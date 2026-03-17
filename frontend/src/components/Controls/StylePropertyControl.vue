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
import { getPresetMap } from "@/utils/presetUtils";
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import blockController from "@/utils/blockController";
import type { Component } from "vue";
import { computed } from "vue";
import { getFontWeightOptions } from "@/utils/fontManager";

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
		property: `${state}:${props.propertyKey}`,
		label: stateLabels[state] || state,
	})),
);

const allVariants = computed(() => [
	...(props.enableStates ? stateVariants.value : []),
	...(props.variants || []),
]);

const getVariantValue = (variantName: string): string | number | boolean => {
	if (stateVariants.value.find((v) => v.name === variantName)) {
		return blockController.getNativeStyle(`${variantName}:${props.propertyKey}`) ?? "";
	}
	const property = props.variants?.find((v) => v.name === variantName)?.property;
	return property ? (blockController.getNativeStyle(property) ?? "") : "";
};

const setVariantValue = (variantName: string, value: string | number | boolean | null) => {
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
		blockController.setStyle(`${variantName}:${props.propertyKey}`, value);
		return;
	}
	const property = props.variants?.find((v) => v.name === variantName)?.property;
	if (property) blockController.setStyle(property, value);
};

const baseProps = computed(() => {
	const { enableStates, enabledStates, variants, ...rest } = props;
	const presetMap = getPresetMap();
	const presetValue = presetMap?.baseStyles?.[props.propertyKey];
	const isInherited =
		presetValue && blockController.getNativeStyle(props.propertyKey as styleProperty) === presetValue;
	return {
		...rest,
		controlType: "style" as const,
		getModelValue:
			props.getModelValue ||
			(() => (isInherited ? "" : String(blockController.getNativeStyle(props.propertyKey) ?? ""))),
		setModelValue:
			props.setModelValue ||
			((value: string | number | boolean) => {
				if (!value && presetValue) {
					blockController.setStyle(props.propertyKey, presetValue);
				} else {
					blockController.setStyle(props.propertyKey, value);
				}
			}),
		getPlaceholder:
			props.getPlaceholder ||
			(() => {
				if (presetValue) {
					if (props.propertyKey === "fontWeight") {
						const options = getFontWeightOptions(
							(blockController.getStyle("fontFamily") as string) || "Inter",
						);
						return options.find((o) => o.value === String(presetValue))?.label || String(presetValue);
					}
					return String(presetValue);
				}
				return String(blockController.getCascadingStyle(props.propertyKey) ?? "unset");
			}),
	};
});
</script>
