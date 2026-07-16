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

		<div class="relative flex w-full items-start gap-2" :data-property="propertyKey">
			<span
				v-if="labelPlacement === 'left' && visibleVariants.length"
				class="pointer-events-none absolute -bottom-2 left-[5.5px] top-5 w-px bg-surface-gray-4"
				aria-hidden="true" />
			<PropertyLabel
				v-if="labelPlacement === 'left' && label"
				ref="propertyLabelRef"
				:label="label"
				:showDropdown="showDropdown"
				:dropdownOptions="dropdownOptions"
				:enableSlider="enableSlider"
				containerClass="h-7 min-w-[88px] w-1/3 shrink-0"
				@mousedown="handleMouseDown" />

			<DraggablePopup
				v-model="showDynamicValueModal"
				:container="propertyLabelRef?.dropdownTrigger"
				placement="middle-right"
				:clickOutsideToClose="false"
				:placementOffset="20"
				v-if="showDynamicValueModal">
				<template #header>Set Dynamic Value</template>
				<template #content>
					<DynamicValueHandler @setDynamicValue="updateDynamicValue" :selectedValue="dynamicValue" />
				</template>
			</DraggablePopup>

			<PropertyControlInput
				:component="props.component"
				:controlAttrs="resolveControlAttrs(null)"
				:events="props.events"
				:modelValue="modelValue"
				:defaultValue="defaultValue"
				:placeholder="placeholderValue"
				:dynamicValueKey="dynamicValue?.key"
				componentClass="w-full"
				@update:modelValue="updateValue"
				@keydown="handleKeyDown"
				@openDynamicModal="showDynamicValueModal = true"
				@clearDynamic="clearDynamicValue">
				<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
					<slot :name="name" v-bind="{ ...slotData, variant: null }" />
				</template>
			</PropertyControlInput>
		</div>

		<!-- Variant controls -->
		<VariantControl
			v-for="(variant, index) in visibleVariants"
			:key="variant.name"
			:data-variant="variant.name"
			:label="variant.label"
			:labelPlacement="labelPlacement"
			:component="props.component"
			:controlAttrs="resolveControlAttrs(variant.name)"
			:events="props.events"
			:modelValue="getDisplayVariantValue(variant.name)"
			:defaultValue="defaultValue"
			:placeholder="placeholderValue"
			:enableSlider="enableSlider"
			:isLast="index === visibleVariants.length - 1"
			@update:modelValue="(v: any) => updateVariantValue(variant.name, v)"
			@keydown="(e: KeyboardEvent) => handleKeyDown(e, variant.name)"
			@labelMousedown="(e: MouseEvent) => handleSliderMouseDown(e, variant.name)"
			@clear="clearVariant(variant.name)">
			<template v-for="(_, name) in $slots" :key="name" #[name]="slotData">
				<slot :name="name" v-bind="{ ...slotData, variant: variant.name }" />
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
import { extractNumberAndUnit, normalizeValueWithUnits, removeDefaultUnit } from "@/utils/helpers";
import type { Component } from "vue";
import { computed, ref, useAttrs } from "vue";

const propertyLabelRef = ref<InstanceType<typeof PropertyLabel> | null>(null);
const emit = defineEmits<{
	(setDynamicValue: string): void;
	(clearDynamicValue: void): void;
}>();

defineOptions({ inheritance: false });

const props = withDefaults(
	defineProps<{
		propertyKey: string;
		label?: string;
		placeholder?: string;
		controlType?: "style" | "attribute" | "key";
		getModelValue?: () => string | number | boolean;
		getPlaceholder?: () => string | number | boolean;
		setModelValue?: (value: string | number | boolean) => void;
		getDynamicValue?: () => { key: string; comesFrom: BlockDataKey["comesFrom"] } | undefined;
		setDynamicValue?: (key: string, comesFrom: BlockDataKey["comesFrom"]) => void;
		enableSlider?: boolean;
		unitOptions?: string[];
		defaultUnit?: string;
		changeFactor?: number;
		minValue?: number;
		maxValue?: number | null;
		component?: Component;
		events?: Record<string, unknown>;
		defaultValue?: string | number;
		allowDynamicValue?: boolean;
		labelPlacement?: "left" | "top";
		variants?: Array<{ name: string; property: string; label: string }>;
		getVariantValue?: (variant: string) => string | number | boolean;
		setVariantValue?: (variant: string, value: string | number | boolean | null) => void;
		getControlAttrs?: (variant: string | null) => Record<string, unknown>;
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

const inheritedControlAttrs = computed(() => {
	const attrs = useAttrs();
	const propKeys = Object.keys(props);
	propKeys.push("style");
	return Object.fromEntries(Object.entries(attrs).filter(([key]) => !propKeys.includes(key)));
});

const resolveControlAttrs = (variant: string | null) => ({
	...inheritedControlAttrs.value,
	...props.getControlAttrs?.(variant),
});

const defaultUnit = computed(() => props.defaultUnit || props.unitOptions[0] || "");

const formatValueForDisplay = (value: string | number | boolean) => {
	if (typeof value !== "string" || !defaultUnit.value) return value;
	return removeDefaultUnit(value, defaultUnit.value);
};

const defaultValue = computed(() => {
	const value = blockController.getCascadingStyle(props.propertyKey) ?? props.defaultValue;
	return value === undefined ? value : formatValueForDisplay(value);
});

const rawModelValue = computed(() => props.getModelValue?.() ?? "");
const modelValue = computed(() => formatValueForDisplay(rawModelValue.value));

const placeholderValue = computed(() => formatValueForDisplay(props.getPlaceholder?.() ?? props.placeholder));

// Normalize and extract value from various input formats
const normalizeInputValue = (
	inputValue: string | number | boolean | null | { label: string; value: string },
) => {
	let value = inputValue;
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	if (typeof value === "number" && defaultUnit.value) {
		value = `${value}${defaultUnit.value}`;
	} else if (typeof value === "string" && defaultUnit.value) {
		value = normalizeValueWithUnits(value, defaultUnit.value);
	}
	return value as string | number | boolean;
};

const updateValue = (value: string | number | boolean | null | { label: string; value: string }) => {
	props.setModelValue?.(normalizeInputValue(value));
};

// Generic slider handler for both main control and variants
const handleSliderMouseDown = (e: MouseEvent, variantName?: string) => {
	if (!props.enableSlider) return;
	const currentValue = variantName ? getRawVariantValue(variantName) : rawModelValue.value;
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

const getRawVariantValue = (variantName: string) => {
	if (props.getVariantValue) {
		return props.getVariantValue(variantName);
	}
	return "";
};

const getDisplayVariantValue = (variantName: string) =>
	formatValueForDisplay(getRawVariantValue(variantName));

const updateVariantValue = (
	variantName: string,
	value: string | number | boolean | null | { label: string; value: string },
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
				.filter((variant) => !getRawVariantValue(variant.name))
				.map((variant) => ({
					label: variant.label,
					onClick: () => {
						if (props.setVariantValue) {
							props.setVariantValue(variant.name, rawModelValue.value as string);
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
	return props.variants.filter((variant) => getRawVariantValue(variant.name));
});

const adjustNumericValue = (step: number, initialValue: number | null = null, variantName?: string) => {
	const currentValue = variantName ? getRawVariantValue(variantName) : String(rawModelValue.value || "");
	const { number, unit: existingUnit } = extractNumberAndUnit(String(currentValue));
	const unit = existingUnit || (!isNaN(Number(number)) ? defaultUnit.value : "");

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

function updateDynamicValue(value: { key: string; comesFrom: BlockDataKey["comesFrom"] }) {
	if (props.setDynamicValue) {
		props.setDynamicValue(value.key, value.comesFrom);
	} else {
		blockController.getSelectedBlocks().forEach((block) => {
			block.setDynamicValue(props.propertyKey, props.controlType, value.key, value.comesFrom);
		});
	}
	showDynamicValueModal.value = false;
	emit("setDynamicValue");
}

const dynamicValue = computed(() => {
	if (props.getDynamicValue) {
		return props.getDynamicValue();
	}
	const blocks = blockController.getSelectedBlocks();
	if (!blocks?.length) return { key: "", comesFrom: "dataScript" as BlockDataKey["comesFrom"] };

	const dataKeyObj = blocks[0]
		.getDynamicValues()
		.find((obj) => obj.type === props.controlType && obj.property === props.propertyKey);
	return { key: dataKeyObj?.key || "", comesFrom: dataKeyObj?.comesFrom || "dataScript" };
});

const clearDynamicValue = () => {
	if (props.setDynamicValue) {
		props.setDynamicValue("", "dataScript");
	} else {
		blockController.getSelectedBlocks().forEach((block) => {
			block.removeDynamicValue(props.propertyKey, props.controlType);
		});
	}
	emit("clearDynamicValue");
};
</script>
