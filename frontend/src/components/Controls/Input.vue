<template>
	<div class="group relative w-full">
		<Select
			v-if="type === 'select'"
			:modelValue="data as string"
			@update:modelValue="(value) => (data = value as typeof data)"
			:disabled="disabled"
			v-bind="attrs" />
		<FormControl
			v-else
			:type="type"
			@change="triggerUpdate"
			@paste="triggerUpdate"
			@cut="triggerUpdate"
			@focus="handleFocus"
			@input="($event: Event) => emit('input', ($event.target as HTMLInputElement).value)"
			autocomplete="off"
			:autofocus="autofocus"
			:disabled="disabled"
			v-bind="attrs"
			:modelValue="data">
			<template #prefix v-if="$slots.prefix">
				<slot name="prefix" />
			</template>
			<template #suffix v-if="$slots.suffix">
				<slot name="suffix" />
			</template>
			<template
				#suffix
				v-else-if="!['select', 'checkbox'].includes(type) && !hideClearButton && data && !disabled">
				<button
					class="cursor-pointer text-ink-gray-4 hover:text-ink-gray-5"
					tabindex="-1"
					:disabled="Boolean(attrs.disabled)"
					@click="clearValue">
					<CrossIcon />
				</button>
			</template>
		</FormControl>

		<div
			v-if="hasNumber && !disabled"
			class="gap-0.1 pointer-events-none absolute right-5 top-1/2 z-10 flex -translate-y-1/2 flex-col opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100">
			<button
				type="button"
				class="duration-250 flex h-3 w-5 items-center justify-center rounded transition-all ease-in-out active:-translate-y-[2px]"
				@click.stop="incrementValue"
				@mousedown.prevent
				tabindex="-1">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="12"
					height="12"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="text-ink-gray-6">
					<polyline points="18 15 12 9 6 15"></polyline>
				</svg>
			</button>
			<button
				type="button"
				class="duration-250 -mt-[2px] flex h-3 w-5 items-center justify-center rounded transition-all ease-in-out active:translate-y-[2px]"
				@click.stop="decrementValue"
				@mousedown.prevent
				tabindex="-1">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="12"
					height="12"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
					class="text-ink-gray-6">
					<polyline points="6 9 12 15 18 9"></polyline>
				</svg>
			</button>
		</div>
	</div>
</template>
<script lang="ts" setup>
import CrossIcon from "@/components/Icons/Cross.vue";
import { useDebounceFn, useVModel } from "@vueuse/core";
import { Select } from "frappe-ui";
import { computed, useAttrs } from "vue";
import { extractNumberAndUnit } from "@/utils/helpers";

const props = withDefaults(
	defineProps<{
		modelValue?: string | number | boolean | null;
		type?: string;
		hideClearButton?: boolean;
		autofocus?: boolean;
		disabled?: boolean;
		selectOnFocus?: boolean;
	}>(),
	{
		type: "text",
		modelValue: "",
		selectOnFocus: true,
	},
);
const emit = defineEmits(["update:modelValue", "input"]);
const data = useVModel(props, "modelValue", emit);

const hasNumber = computed(() => {
	if (!data.value) return false;
	const value = String(data.value).trim();
	return /^-?\d/.test(value); //
});

defineOptions({
	inheritAttrs: false,
});

const attrs = useAttrs();

const clearValue = () => {
	data.value = "";
};

const triggerUpdate = useDebounceFn(($event: Event) => {
	if (props.type === "checkbox") {
		emit("update:modelValue", ($event.target as HTMLInputElement).checked);
	} else {
		emit("update:modelValue", ($event.target as HTMLInputElement).value);
	}
}, 100);

const handleFocus = ($event: Event) => {
	if (props.selectOnFocus && !props.disabled && props.type !== "checkbox") {
		const target = $event.target as HTMLInputElement;
		setTimeout(() => {
			target.select();
		}, 0);
	}
};

const incrementValue = () => {
	const { number, unit } = extractNumberAndUnit(String(data.value || ""));
	const step = props.type === "number" && attrs.step ? parseFloat(String(attrs.step)) : 1;
	const max = attrs.max !== undefined ? parseFloat(String(attrs.max)) : Infinity;
	const min = attrs.min !== undefined ? parseFloat(String(attrs.min)) : -Infinity;
	const currentNum = parseFloat(number) || 0;
	const newNum = Math.min(max, parseFloat((currentNum + step).toFixed(10)));
	const newValue = newNum + unit;
	data.value = newValue;
	emit("update:modelValue", newValue);
};

const decrementValue = () => {
	const { number, unit } = extractNumberAndUnit(String(data.value || ""));
	const step = props.type === "number" && attrs.step ? parseFloat(String(attrs.step)) : 1;
	const max = attrs.max !== undefined ? parseFloat(String(attrs.max)) : Infinity;
	const min = attrs.min !== undefined ? parseFloat(String(attrs.min)) : -Infinity;
	const currentNum = parseFloat(number) || 0;
	const newNum = Math.max(min, parseFloat((currentNum - step).toFixed(10)));
	const newValue = newNum + unit;
	data.value = newValue;
	emit("update:modelValue", newValue);
};
</script>

<style>
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
	-webkit-appearance: none !important;
	margin: 0 !important;
}

input[type="number"] {
	-moz-appearance: textfield !important;
	appearance: textfield !important;
	padding-right: 0.75rem !important;
}
</style>
