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

		<NumberArrows
			:modelValue="hasNumber"
			:disabled="disabled"
			@increment="incrementValue"
			@decrement="decrementValue" />
	</div>
</template>
<script lang="ts" setup>
import CrossIcon from "@/components/Icons/Cross.vue";
import { useDebounceFn, useVModel } from "@vueuse/core";
import { Select } from "frappe-ui";
import { computed, useAttrs } from "vue";
import { useNumberInput } from "@/utils/useNumberInput";
import NumberArrows from "@/components/Controls/NumberArrows.vue";

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

interface UseNumberInputOptions {
	getValue: () => string | number | boolean | null | undefined;
	setValue: (value: string) => void;
	getAttrs?: () => Record<string, unknown>;
}

defineOptions({
	inheritAttrs: false,
});

const attrs = useAttrs();

const { hasNumber, incrementValue, decrementValue } = useNumberInput({
	getValue: () => data.value,
	setValue: (v) => {
		data.value = v;
		emit("update:modelValue", v);
	},
	getAttrs: () => attrs,
});

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
