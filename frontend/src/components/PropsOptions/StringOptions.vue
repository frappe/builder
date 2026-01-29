<template>
	<div class="flex items-center justify-between">
		<InputLabel>Default Value</InputLabel>
		<Input
			:model-value="options.defaultValue"
			@input="handleDefaultValueChange"
			@update:model-value="handleDefaultValueChange"
			placeholder="Enter default value"></Input>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import { ref } from "vue";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

const defaultValue = ref(props.options?.defaultValue);

const handleDefaultValueChange = (value: string) => {
	defaultValue.value = value;
	emit("update:options", {
		defaultValue: value,
	});
};

const reset = (toProps: boolean = false) => {
	defaultValue.value = toProps ? props.options?.defaultValue : "";
};

defineExpose({ reset });
</script>
