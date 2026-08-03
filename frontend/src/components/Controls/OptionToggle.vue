<template>
	<div class="flex w-full items-center justify-between">
		<InputLabel v-if="label">{{ label }}</InputLabel>
		<TabButtons
			:class="['w-full min-w-[150px]', STRETCH_TABS]"
			:options="tabOptions"
			:modelValue="modelValue"
			@update:modelValue="$emit('update:modelValue', $event)" />
	</div>
</template>
<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { STRETCH_TABS } from "@/utils/tabButtons";
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

// the value a block inherits when it doesn't set the property itself is outlined
// rather than selected, so the panel never claims a style that isn't there
const INHERITED_OUTLINE = "outline-dashed outline-1 -outline-offset-1 outline-[color:var(--outline-gray-3)]";

const isSet = computed(
	() => props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "",
);

const tabOptions = computed(() =>
	props.options.map(({ label, value, icon, hideLabel, showTooltip }) => ({
		value,
		// frappe-ui reads `icon` as icon-only, `iconLeft` as an accent beside the label
		...(hideLabel ? { icon } : { label, iconLeft: icon }),
		tooltip: hideLabel || showTooltip ? label : undefined,
		class: !isSet.value && (value ?? label) === props.defaultValue ? INHERITED_OUTLINE : undefined,
	})),
);
</script>
