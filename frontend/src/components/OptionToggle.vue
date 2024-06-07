<template>
	<div class="flex w-full items-center justify-between">
		<InputLabel v-if="label">{{ label }}</InputLabel>
		<TabButtons
			class="w-[140px] [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-800"
			:buttons="options"
			:modelValue="modelValue"
			@update:modelValue="$emit('update:modelValue', $event)"></TabButtons>
	</div>
</template>
<script setup lang="ts">
import { TabButtons } from "frappe-ui";
import { PropType } from "vue";
import InputLabel from "./InputLabel.vue";

defineProps({
	modelValue: {
		type: [String, Number, Boolean],
	},
	options: {
		type: Array as PropType<{ label: string; value: string | number }[]>,
		default: () => [],
	},
	label: {
		type: String,
		default: "",
	},
});

const emit = defineEmits(["update:modelValue"]);
</script>
