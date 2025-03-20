<template>
	<div class="flex w-full items-center justify-between">
		<InputLabel v-if="label">{{ label }}</InputLabel>
		<TabButtons
			class="w-full min-w-[150px] [&>div>button[aria-checked='true']]:dark:!bg-surface-gray-4 [&>div>button]:items-center [&>div]:h-7"
			:buttons="options"
			:modelValue="modelValue"
			@update:modelValue="$emit('update:modelValue', $event)"></TabButtons>
	</div>
</template>
<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { TabButtons } from "frappe-ui";

withDefaults(
	defineProps<{
		modelValue: string | number | boolean;
		options?: { label: string; value: string | number; icon?: string; hideLabel?: boolean }[];
		label?: string;
	}>(),
	{
		options: () => [],
		label: "",
	},
);

const emit = defineEmits(["update:modelValue"]);
</script>
