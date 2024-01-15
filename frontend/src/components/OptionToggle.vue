<template>
	<div class="flex items-center justify-between">
		<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
			{{ label }}
		</span>
		<TabButtons
			class="[&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"
			:buttons="options"
			:modelValue="modelValue"
			@update:modelValue="$emit('update:modelValue', $event)"></TabButtons>
	</div>
</template>
<script setup lang="ts">
import { TabButtons } from "frappe-ui";
import { PropType } from "vue";

defineProps({
	modelValue: {
		type: String,
	},
	options: {
		type: Array as PropType<{ label: string; value: string }[]>,
		default: () => [],
	},
	label: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue"]);
</script>
