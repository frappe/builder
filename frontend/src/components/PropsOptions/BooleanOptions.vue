<template>
	<div class="flex items-center justify-between">
		<InputLabel>True Option</InputLabel>
		<Input
			:model-value="trueOption"
			@update:model-value="handleTrueOptionChange"
			@input="handleTrueOptionChange"
			placeholder="Enter true option display"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>False Option</InputLabel>
		<Input
			:model-value="falseOption"
			@update:model-value="handleFalseOptionChange"
			@input="handleFalseOptionChange"
			placeholder="Enter false option display"></Input>
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
			trueOption,
			falseOption,
			defaultValue,
		});
	}

	return { value, reset, handleChange };
}

const { value: trueOption, reset: resetTrueOption, handleChange: handleTrueOptionChange } = useBooleanOption("trueOption");
const { value: falseOption, reset: resetFalseOption, handleChange: handleFalseOptionChange } = useBooleanOption("falseOption");
const { value: defaultValue, reset: resetDefaultValue, handleChange: handleDefaultValueChange } = useBooleanOption("defaultValue");

const reset = (toProps: boolean = false) => {
	resetTrueOption(toProps);
	resetFalseOption(toProps);
	resetDefaultValue(toProps);
};

defineExpose({ reset });
</script>
