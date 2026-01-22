<template>
	<div class="flex items-center justify-between">
		<InputLabel>Default Value</InputLabel>
		<ColorInput
			class="w-full"
			fix-to=".props-popover-content"
			placement="right"
			:make-fixed="true"
			:model-value="options.defaultValue"
			@update:model-value="handleDefaultValueChange"
			placeholder="Select default color"></ColorInput>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { ref } from "vue";
import ColorInput from "../Controls/ColorInput.vue";

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
