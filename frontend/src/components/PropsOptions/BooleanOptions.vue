<template>
	<div class="flex items-center justify-between">
		<InputLabel>True Label</InputLabel>
		<Input
			:model-value="trueLabel"
			@update:model-value="handleTrueLabelChange"
			@input="handleTrueLabelChange"
			placeholder="Enter true Label display"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>False Label</InputLabel>
		<Input
			:model-value="falseLabel"
			@update:model-value="handleFalseLabelChange"
			@input="handleFalseLabelChange"
			placeholder="Enter false Label display"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>Default Value</InputLabel>
		<Input
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
			@update:model-value="handleDefaultValueChange"
			placeholder="Enter default value"></Input>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import { nextTick, ref, watch } from "vue";

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

const { value: trueLabel, reset: resetTrueLabel, handleChange: handleTrueLabelChange } = useBooleanOption("trueLabel");
const { value: falseLabel, reset: resetFalseLabel, handleChange: handleFalseLabelChange } = useBooleanOption("falseLabel");
const { value: defaultValue, reset: resetDefaultValue, handleChange: handleDefaultValueChange } = useBooleanOption("defaultValue");

const reset = (toProps: boolean = false) => {
	resetTrueLabel(toProps);
	resetFalseLabel(toProps);
	resetDefaultValue(toProps);
};

defineExpose({ reset });
</script>
