<template>
	<div class="flex w-full items-center justify-between">
		<InputLabel v-if="label" class="w-1/3 min-w-[88px] shrink-0">{{ label }}</InputLabel>
		<TabButtons
			fluid
			class="w-full min-w-[150px] [&_[data-slot=tab-button]]:relative"
			:options="tabOptions"
			:modelValue="toTabValue(modelValue)"
			@update:modelValue="$emit('update:modelValue', fromTabValue($event))">
			<template #prefix="{ button }">
				<span v-if="isInherited(button.value)" :class="INHERITED_OUTLINE" />
			</template>
		</TabButtons>
	</div>
</template>
<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import { TabButtons, type TabButtonValue } from "frappe-ui";
import { computed, type Component } from "vue";

type ToggleValue = TabButtonValue | boolean;

const props = withDefaults(
	defineProps<{
		modelValue?: ToggleValue;
		options?: {
			label: string;
			value: ToggleValue;
			icon?: string | Component;
			hideLabel?: boolean;
		}[];
		label?: string;
		defaultValue?: ToggleValue;
	}>(),
	{
		options: () => [],
		label: "",
	},
);

defineEmits(["update:modelValue"]);

// the value a block inherits when it doesn't set the property itself is outlined
// rather than selected, so the panel never claims a style that isn't there.
// frappe-ui owns the tab markup, so it goes in through the prefix slot. The slot
// wrapper has no radius to inherit, so this repeats the sm subtle tab's 7px.
const INHERITED_OUTLINE =
	"pointer-events-none absolute inset-0 rounded-[7px] outline-dashed outline-1 -outline-offset-1 outline-[color:var(--outline-gray-3)]";

const isSet = computed(
	() => props.modelValue !== undefined && props.modelValue !== null && props.modelValue !== "",
);

const isInherited = (value: TabButtonValue) => !isSet.value && value === toTabValue(props.defaultValue);

// TabButtons only takes strings and numbers, so boolean options (component props of type
// boolean) go through as "true"/"false" and are emitted back as booleans
const toTabValue = (value?: ToggleValue) => (typeof value === "boolean" ? String(value) : value);

const fromTabValue = (value: TabButtonValue) =>
	props.options.find((option) => toTabValue(option.value) === value)?.value ?? value;

const tabOptions = computed(() =>
	props.options.map(({ label, value, icon, hideLabel }) => ({
		value: toTabValue(value) as TabButtonValue,
		label,
		// frappe-ui reads `icon` as icon-only, labelling the tab with `label`,
		// and `iconLeft` as an accent beside a visible label
		...(hideLabel ? { icon } : { iconLeft: icon }),
	})),
);
</script>
