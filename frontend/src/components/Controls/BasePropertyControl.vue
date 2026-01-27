<template>
	<div class="flex w-full flex-col gap-2">
		<PropertyLabel
			v-if="labelPlacement === 'top' && label"
			ref="propertyLabelRef"
			:label="label"
			:showDropdown="showDropdown"
			:dropdownOptions="dropdownOptions"
			:enableSlider="enableSlider"
			@mousedown="handleMouseDown" />

		<div
			class="relative flex w-full gap-2"
			:class="labelPlacement === 'top' ? 'items-start' : 'items-center'">
			<PropertyLabel
				v-if="labelPlacement === 'left' && label"
				ref="propertyLabelRef"
				:label="label"
				:showDropdown="showDropdown"
				:dropdownOptions="dropdownOptions"
				:enableSlider="enableSlider"
				containerClass="w-[88px] shrink-0"
				@mousedown="handleMouseDown" />

			<DraggablePopup
				v-model="showDynamicValueModal"
				:container="propertyLabelRef?.dropdownTrigger?.$el"
				placement="middle-right"
				:clickOutsideToClose="false"
				:placementOffset="20"
				v-if="showDynamicValueModal">
				<template #header>Set Dynamic Value</template>
				<template #content>
					<DynamicValueHandler @setDynamicValue="setDynamicValue" :selectedValue="dynamicValue" />
				</template>
			</DraggablePopup>

			<PropertyControlInput
				:component="props.component"
				:controlAttrs="controlAttrs"
				:events="props.events"
				:modelValue="modelValue"
				:defaultValue="defaultValue"
				:placeholder="placeholderValue"
				:dynamicValue="dynamicValue"
				componentClass="w-full"
				@update:modelValue="updateValue"
				@keydown="handleKeyDown"
				@openDynamicModal="showDynamicValueModal = true"
				@clearDynamic="clearDynamicValue">
				<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
					<slot :name="name" v-bind="slotData || {}" />
				</template>
			</PropertyControlInput>
		</div>

		<!-- Variant controls -->
		<VariantControl
			v-for="variant in visibleVariants"
			:key="variant.name"
			:label="variant.label"
			:labelPlacement="labelPlacement"
			:component="props.component"
			:controlAttrs="controlAttrs"
			:events="props.events"
			:modelValue="getVariantValue(variant.name)"
			:defaultValue="defaultValue"
			:placeholder="placeholderValue"
			:enableSlider="enableSlider"
			@update:modelValue="(v: any) => updateVariantValue(variant.name, v)"
			@keydown="(e: KeyboardEvent) => handleKeyDown(e, variant.name)"
			@labelMousedown="(e: MouseEvent) => handleSliderMouseDown(e, variant.name)"
			@clear="clearVariant(variant.name)">
			<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
				<slot :name="name" v-bind="slotData || {}" />
			</template>
		</VariantControl>
	</div>
</template>

<script lang="ts" setup>
import DynamicValueHandler from "@/components/Controls/DynamicValueHandler.vue";
import Input from "@/components/Controls/Input.vue";
import PropertyControlInput from "@/components/Controls/PropertyControlInput.vue";
import PropertyLabel from "@/components/Controls/PropertyLabel.vue";
import VariantControl from "@/components/Controls/VariantControl.vue";
import blockController from "@/utils/blockController";
import { extractNumberAndUnit, normalizeValueWithUnits } from "@/utils/helpers";
import type { Component } from "vue";
import { computed, ref, useAttrs } from "vue";

const propertyLabelRef = ref<InstanceType<typeof PropertyLabel> | null>(null);
const emit = defineEmits<{
	(setDynamicValue: string): void;
	(clearDynamicValue: void): void;
}>();

const props = withDefaults(
	defineProps<{
		propertyKey: string;
		label?: string;
		placeholder?: string;
		controlType?: "style" | "attribute" | "key";
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
		variants?: Array<{ name: string; property: string; label: string }>;
		getVariantValue?: (variant: string) => string;
		setVariantValue?: (variant: string, value: string | null) => void;
	}>(),
	{
		placeholder: "unset",
		controlType: "style",
		enableSlider: false,
		unitOptions: () => [],
		changeFactor: 1,
		minValue: 0,
		maxValue: null,
		component: Input,
		allowDynamicValue: false,
		labelPlacement: "left",
		variants: () => [],
	},
);

const showDropdown = computed(() => {
	return props.allowDynamicValue || (props.variants && props.variants.length > 0);
});

const controlAttrs = computed(() => {
	const attrs = useAttrs();
	const propKeys = Object.keys(props);
	propKeys.push("style");
	return Object.fromEntries(Object.entries(attrs).filter(([key]) => !propKeys.includes(key)));
});

const defaultValue = computed(() => {
	return blockController.getCascadingStyle(props.propertyKey) ?? props.defaultValue;
});

const modelValue = computed(() => props.getModelValue?.() ?? "");

const placeholderValue = computed(() => props.getPlaceholder?.() ?? props.placeholder);

// Normalize and extract value from various input formats
const normalizeInputValue = (value: string | number | null | { label: string; value: string }) => {
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	if (value && typeof value === "string") {
		value = normalizeValueWithUnits(value, props.unitOptions, props.propertyKey);
	}
	return value as string;
};

const updateValue = (value: string | number | null | { label: string; value: string }) => {
	props.setModelValue?.(normalizeInputValue(value));
};

// Generic slider handler for both main control and variants
const handleSliderMouseDown = (e: MouseEvent, variantName?: string) => {
	if (!props.enableSlider) return;
	const currentValue = variantName ? getVariantValue(variantName) : modelValue.value;
	const { number } = extractNumberAndUnit(String(currentValue || ""));
	const startY = e.clientY;
	const startValue = Number(number);

	const handleMouseMove = (e: MouseEvent) => {
		const diff = Math.round((startY - e.clientY) * props.changeFactor);
		adjustNumericValue(diff, startValue, variantName);
	};

	const handleMouseUp = () => window.removeEventListener("mousemove", handleMouseMove);

	window.addEventListener("mousemove", handleMouseMove);
	window.addEventListener("mouseup", handleMouseUp, { once: true });
};

const handleMouseDown = (e: MouseEvent) => handleSliderMouseDown(e);

const getVariantValue = (variantName: string) => {
	if (props.getVariantValue) {
		return props.getVariantValue(variantName);
	}
	return "";
};

const updateVariantValue = (
	variantName: string,
	value: string | number | null | { label: string; value: string },
) => {
	props.setVariantValue?.(variantName, normalizeInputValue(value));
};

const clearVariant = (variantName: string) => props.setVariantValue?.(variantName, null);

const showDynamicValueModal = ref(false);

const dropdownOptions = computed(() => {
	const options = [];
	if (props.variants?.length) {
		options.push(
			...props.variants
				.filter((variant) => !getVariantValue(variant.name))
				.map((variant) => ({
					label: variant.label,
					onClick: () => {
						if (props.setVariantValue) {
							props.setVariantValue(variant.name, modelValue.value as string);
						}
					},
				})),
		);
	}

	if (props.allowDynamicValue) {
		options.unshift({
			label: "Set Dynamic Value",
			onClick: () => {
				showDynamicValueModal.value = true;
			},
		});
	}
	return options;
});

const visibleVariants = computed(() => {
	if (!props.variants?.length) return [];
	return props.variants.filter((variant) => getVariantValue(variant.name));
});

const adjustNumericValue = (step: number, initialValue: number | null = null, variantName?: string) => {
	const currentValue = variantName ? getVariantValue(variantName) : String(modelValue.value || "");
	const { number, unit: existingUnit } = extractNumberAndUnit(String(currentValue));
	const unit =
		existingUnit || (props.unitOptions.length && !isNaN(Number(number)) ? props.unitOptions[0] : "");

	let newValue = (initialValue != null ? initialValue : Number(number)) + step;
	newValue = Math.max(props.minValue, Math.min(props.maxValue ?? Infinity, newValue));

	const result = newValue + unit;
	variantName ? updateVariantValue(variantName, result) : updateValue(result);
};

const handleKeyDown = (e: KeyboardEvent, variantName?: string) => {
	if (!props.enableSlider || (e.key !== "ArrowUp" && e.key !== "ArrowDown")) return;

	const step = e.key === "ArrowUp" ? 1 : -1;
	adjustNumericValue(step, null, variantName);
	e.preventDefault();
};

function setDynamicValue(value: string) {
	blockController.getSelectedBlocks().forEach((block) => {
		block.setDynamicValue(props.propertyKey, props.controlType, value);
	});
	showDynamicValueModal.value = false;
	emit("setDynamicValue");
}

const dynamicValue = computed(() => {
	const blocks = blockController.getSelectedBlocks();
	if (!blocks?.length) return "";

	const dataKeyObj = blocks[0]
		.getDynamicValues()
		.find((obj) => obj.type === props.controlType && obj.property === props.propertyKey);
	return dataKeyObj?.key || "";
});

const clearDynamicValue = () => {
	blockController.getSelectedBlocks().forEach((block) => {
		block.removeDynamicValue(props.propertyKey, props.controlType);
	});
	emit("clearDynamicValue");
};
</script>
