<template>
	<div v-if="false" class="flex items-center justify-between">
		<InlineInput
			label="Min. Value"
			:modelValue="minValue"
			@update:modelValue="handleMinValueChange"
			@input="handleMinValueChange"
			placeholder="Enter min value"></InlineInput>
	</div>
	<div v-if="false" class="flex items-center justify-between">
		<InlineInput
			label="Max. Value"
			:modelValue="maxValue"
			@update:modelValue="handleMaxValueChange"
			placeholder="Enter max value"></InlineInput>
	</div>
	<div class="flex items-center justify-between">
		<InlineInput
			label="Default Value"
			:modelValue="defaultValue"
			@update:modelValue="handleDefaultValueChange"
			@input="handleDefaultValueChange"
			@update:model-value="handleMaxValueChange"
			placeholder="Enter max value"></InlineInput>
	</div>
	<div class="flex items-center justify-between">
		<InlineInput
			label="Default Value"
			:modelValue="defaultValue"
			@update:modelValue="handleDefaultValueChange"
			@input="handleDefaultValueChange"
			placeholder="Enter default value"></InlineInput>
	</div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import { toast } from "vue-sonner";
import InlineInput from "@/components/Controls/InlineInput.vue";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

// helper to coerce values to number or null
function toNumberOrNull(v: any) {
	const n = parseFloat(v);
	return Number.isFinite(n) ? n : null;
}

function performValidation() {
	const min = toNumberOrNull(minValue.value);
	const max = toNumberOrNull(maxValue.value);
	const def = toNumberOrNull(defaultValue.value);

	let isValid = true;
	if (min !== null && max !== null && min > max) {
		isValid = false;
	}
	if (def !== null) {
		if (min !== null && def < min) {
			isValid = false;
		}
		if (max !== null && def > max) {
			isValid = false;
		}
	}
	return isValid;
}

function useNumericOption(key: string) {
	const value = ref(toNumberOrNull(props.options?.[key]));

	watch(
		() => props.options?.[key],
		(newVal) => {
			value.value = toNumberOrNull(newVal);
		},
	);

	function reset(toProps: boolean) {
		if (toProps) {
			value.value = toNumberOrNull(props.options?.[key]);
		} else {
			value.value = null;
		}
	}

	async function handleChange(val: string) {
		const parsed = toNumberOrNull(val);
		value.value = parsed;
		await nextTick();
		const isValid = performValidation();
		if (isValid) {
			emit("update:options", {
				minValue: minValue.value,
				maxValue: maxValue.value,
				defaultValue: defaultValue.value,
			});
		} else {
			toast.error("Invalid option configuration!");
		}
	}

	return { value, reset, handleChange };
}

const {
	value: minValue,
	reset: resetMinValue,
	handleChange: handleMinValueChange,
} = useNumericOption("minValue");
const {
	value: maxValue,
	reset: resetMaxValue,
	handleChange: handleMaxValueChange,
} = useNumericOption("maxValue");
const {
	value: defaultValue,
	reset: resetDefaultValue,
	handleChange: handleDefaultValueChange,
} = useNumericOption("defaultValue");

const reset = (toProps = false) => {
	resetMinValue(toProps);
	resetMaxValue(toProps);
	resetDefaultValue(toProps);
};

defineExpose({ reset });
</script>
