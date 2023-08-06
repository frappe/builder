<template>
	<div>
		<Combobox :modelValue="value" @update:modelValue="(val) => emit('update:modelValue', val)" nullable>
			<ComboboxInput
				autocomplete="off"
				@change="query = $event.target.value"
				:displayValue="(option: Option) => (option ? option.label : '')"
				:placeholder="placeholder"
				class="flex h-7 w-full items-center justify-between gap-2 rounded bg-gray-100 px-2 py-1 pr-6 text-sm text-gray-800 outline-none transition-colors hover:bg-gray-200 focus:ring-2 focus:ring-gray-400 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-200 dark:focus:bg-zinc-700" />
			<ComboboxOptions
				class="absolute right-0 z-50 max-h-[15rem] w-full max-w-[150px] overflow-y-auto rounded-lg bg-white px-1.5 py-1.5 shadow-2xl"
				v-show="filteredValues.length">
				<ComboboxOption v-if="query" :value="query" class="flex items-center"></ComboboxOption>
				<ComboboxOption
					v-slot="{ active, selected }"
					v-for="option in filteredValues"
					:key="option.value"
					:value="option"
					class="flex items-center">
					<li
						class="w-full select-none rounded px-2.5 py-1.5 text-xs"
						:class="{
							'bg-gray-100': active,
							'bg-gray-300': selected,
						}">
						{{ option.label }}
					</li>
				</ComboboxOption>
			</ComboboxOptions>
		</Combobox>
		<div
			class="absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
			@click="clearValue"
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
import { Combobox, ComboboxInput, ComboboxOption, ComboboxOptions } from "@headlessui/vue";
import { ComputedRef, PropType, computed, ref } from "vue";
const query = ref("");

const filteredValues = computed(() =>
	query.value === ""
		? props.options
		: props.options.filter((option) => {
				return option.value.toLowerCase().includes(query.value.toLowerCase());
		  })
);

type Option = {
	label: string;
	value: string;
};
const props = defineProps({
	options: {
		type: Array as PropType<Option[]>,
		default: () => [],
	},
	modelValue: {},
	placeholder: {
		type: String,
		default: "Search",
	},
});
const value = computed(() => {
	if (
		props.modelValue instanceof String ||
		typeof props.modelValue === "string" ||
		props.modelValue instanceof Number ||
		typeof props.modelValue === "number"
	) {
		return { label: props.modelValue, value: props.modelValue };
	} else {
		return props.modelValue;
	}
}) as ComputedRef<Option>;
const emit = defineEmits(["update:modelValue"]);
const clearValue = () => emit("update:modelValue", null);
</script>
