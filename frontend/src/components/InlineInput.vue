<template>
	<div class="relative flex items-center justify-between">
		<span class="inline-block text-[10px] font-medium uppercase text-gray-600 dark:text-zinc-400">
			{{ label }}
		</span>
		<Input
			:type="type"
			placeholder="unset"
			:value="modelValue"
			:options="inputOptions"
			v-if="type != 'autocomplete'"
			@change="handleChange"
			:inputClass="type == 'checkbox' ? ' ml-2 !w-4' : 'pr-6'"
			class="rounded-md text-sm text-gray-800 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700"
			:class="{
				'w-[150px]': type != 'checkbox',
			}" />
		<Autocomplete
			v-if="type == 'autocomplete'"
			placeholder="unset"
			:modelValue="modelValue"
			:options="inputOptions"
			@update:modelValue="handleChange"
			class="!dark:text-zinc-200 !dark:focus:bg-zinc-700 w-[150px] rounded-md text-sm text-gray-800 dark:bg-zinc-800" />
		<div
			class="absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
			@click="clearValue"
			v-if="!['autocomplete', 'select', 'checkbox'].includes(type)"
			v-show="modelValue">
			<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24">
				<path
					fill="currentColor"
					d="M18.3 5.71a.996.996 0 0 0-1.41 0L12 10.59L7.11 5.7A.996.996 0 1 0 5.7 7.11L10.59 12L5.7 16.89a.996.996 0 1 0 1.41 1.41L12 13.41l4.89 4.89a.996.996 0 1 0 1.41-1.41L13.41 12l4.89-4.89c.38-.38.38-1.02 0-1.4z" />
			</svg>
		</div>
	</div>
</template>
<script setup lang="ts">
import { computed } from "vue";
import Autocomplete from "./Autocomplete.vue";

const props = defineProps({
	modelValue: {},
	label: {
		type: String,
		default: "",
	},
	type: {
		type: String,
		default: "text",
	},
	unitOptions: {
		type: Array,
		default: () => [],
	},
	options: {
		type: Array,
		default: () => [],
	},
});

const emit = defineEmits(["update:modelValue"]);

type Option = {
	label: string;
	value: string;
};

const inputOptions = computed(() => {
	return (props.options || []).map((option) => {
		if (typeof option === "string" || (typeof option === "number" && props.type === "autocomplete")) {
			return {
				label: option,
				value: option,
			};
		}
		return option;
	}) as Option[];
});

const handleChange = (value: string | number | null | { label: string; value: string }) => {
	if (typeof value === "object" && value !== null && "value" in value) {
		value = value.value;
	}
	emit("update:modelValue", value);
};

const clearValue = () => emit("update:modelValue", null);
</script>
