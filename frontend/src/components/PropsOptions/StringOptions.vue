<template>
	<div class="flex items-center justify-between">
		<InlineInput
			label="Default Value"
			class="w-full"
			:modelValue="defaultValue"
			@update:modelValue="handleDefaultValueChange"
			placeholder="Enter default value"></InlineInput>
	</div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import InlineInput from "@/components/Controls/InlineInput.vue";

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
