<template>
	<div class="flex items-center justify-between">
		<InlineInput
			label="True Label"
			class="w-full"
			:modelValue="trueLabel"
			@update:modelValue="handleTrueLabelChange"
			placeholder="Enter true label display"></InlineInput>
	</div>
	<div class="flex items-center justify-between">
		<InlineInput
			label="False Label"
			class="w-full"
			:modelValue="falseLabel"
			@update:modelValue="handleFalseLabelChange"
			placeholder="Enter false label display"></InlineInput>
	</div>
	<div class="flex items-center justify-between">
		<InlineInput
			label="Default Value"
			class="w-full"
			type="select"
			:options="[
				{
					label: 'true',
					value: 'true',
				},
				{
					label: 'false',
					value: 'false',
				},
			]"
			:modelValue="defaultValue"
			@update:modelValue="handleDefaultValueChange"
			placeholder="Enter default value"></InlineInput>
	</div>
</template>

<script setup lang="ts">
import { nextTick, ref, watch } from "vue";
import InlineInput from "@/components/Controls/InlineInput.vue";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

function useBooleanOption(key: string) {
	const value = ref(props.options?.[key]);

	watch(
		() => props.options?.[key],
		(newVal) => {
			value.value = newVal;
		},
	);

	function reset(toProps: boolean = false) {
		value.value = toProps ? props.options?.[key] : "";
	}

	async function handleChange(val: string) {
		value.value = val;
		await nextTick();
		emit("update:options", {
			trueLabel: trueLabel.value,
			falseLabel: falseLabel.value,
			defaultValue: defaultValue.value,
		});
	}

	return { value, reset, handleChange };
}

const {
	value: trueLabel,
	reset: resetTrueLabel,
	handleChange: handleTrueLabelChange,
} = useBooleanOption("trueLabel");
const {
	value: falseLabel,
	reset: resetFalseLabel,
	handleChange: handleFalseLabelChange,
} = useBooleanOption("falseLabel");
const {
	value: defaultValue,
	reset: resetDefaultValue,
	handleChange: handleDefaultValueChange,
} = useBooleanOption("defaultValue");

const reset = (toProps: boolean = false) => {
	resetTrueLabel(toProps);
	resetFalseLabel(toProps);
	resetDefaultValue(toProps);
};

defineExpose({ reset });
</script>
