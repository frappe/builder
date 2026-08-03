<template>
	<div class="flex w-full items-center justify-between">
		<InputLabel v-if="label">{{ label }}</InputLabel>
		<TabButtons
			class="w-full min-w-[150px] [&>div]:w-full [&_[data-slot=tab-button]>span]:w-full [&_[data-slot=tab-button]]:flex-1"
			:options="tabOptions"
			:modelValue="modelValue"
			@update:modelValue="$emit('update:modelValue', $event)" />
	</div>
</template>
<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { TabButtons } from "frappe-ui";
import { computed, type Component } from "vue";

const props = withDefaults(
	defineProps<{
		modelValue?: string | number | boolean;
		options?: {
			label: string;
			value: string | number | boolean;
			icon?: string | Component;
			hideLabel?: boolean;
			showTooltip?: boolean;
		}[];
		label?: string;
		defaultValue?: string | number;
	}>(),
	{
		options: () => [],
		label: "",
	},
);

defineEmits(["update:modelValue"]);

const isSet = computed(
	() => props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "",
);

const tabOptions = computed(() =>
	props.options.map((option) => ({
		value: option.value,
		label: option.hideLabel ? undefined : option.label,
		// an `icon` renders icon-only, `iconLeft` alongside the label
		icon: option.hideLabel ? option.icon : undefined,
		iconLeft: option.hideLabel ? undefined : option.icon,
		tooltip: option.hideLabel || option.showTooltip ? option.label : undefined,
		// a property the block doesn't set: outline the value it inherits instead of
		// selecting it, so the panel never claims a style that isn't there
		class:
			!isSet.value && (option.value ?? option.label) === props.defaultValue
				? "outline-dashed outline-1 -outline-offset-1 outline-[color:var(--outline-gray-3)]"
				: undefined,
	})),
);
</script>
