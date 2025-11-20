<template>
	<div class="flex items-center justify-between">
		<InputLabel>Min. Items</InputLabel>
		<Input
			:model-value="minItems"
			@update:model-value="handleMinItemsChange"
			@input="handleMinItemsChange"
			placeholder="Enter min number of items"></Input>
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>Max. Items</InputLabel>
		<Input
			:model-value="maxItems"
			@update:model-value="handleMaxItemsChange"
			@input="handleMaxItemsChange"
			placeholder="Enter max number of items"></Input>
	</div>
	<div class="flex flex-col gap-3">
		<InputLabel>Default Items</InputLabel>
		<ArrayEditor :arr @update:arr="handleArrChange" />
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import ArrayEditor from "@/components/ArrayEditor.vue";
import { nextTick, ref, watch } from "vue";
import { Ref } from "vue";
import { toast } from "vue-sonner";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

type NumberRef = {
	value: Ref<number | null, number | null>;
	handleChange: (val: string) => Promise<void>;
	reset: (toProps?: boolean) => void;
};

type StringArrayRef = {
	value: Ref<string[], string[]>;
	handleChange: (val: any[]) => Promise<void>;
	reset: (toProps?: boolean) => void;
};

function toNumberOrNull(v: any) {
	const n = parseFloat(v);
	return Number.isFinite(n) ? n : null;
}

function performValidation() {
	const min = toNumberOrNull(minItems.value);
	const max = toNumberOrNull(maxItems.value);
	const def = arr.value.length;
	let isValid = true;
	if (min !== null && max !== null && min > max) {
		isValid = false;
	}
	if (def) {
		if (min !== null && def < min) {
			isValid = false;
		}
		if (max !== null && def > max) {
			isValid = false;
		}
	}
	return isValid;
}

function useArrayOption(key: string, isNumeric: boolean = false) {
	const numericValue = ref(toNumberOrNull(props.options?.[key]));
	const arrayValue = ref<string[]>(Array.isArray(props.options?.[key]) ? props.options?.[key] : []);

	watch(
		() => props.options?.[key],
		(newVal) => {
			if (isNumeric) {
				numericValue.value = toNumberOrNull(newVal);
			} else {
				arrayValue.value = Array.isArray(newVal) ? newVal : [];
			}
		},
	);

	function resetNumber(toProps: boolean) {
		numericValue.value = toProps ? toNumberOrNull(props.options?.[key]) : null;
	}
	function resetArray(toProps: boolean) {
		arrayValue.value = toProps && Array.isArray(props.options?.[key]) ? props.options?.[key] : [];
	}

	async function handleNumberChange(val: string) {
		numericValue.value = toNumberOrNull(val);
		await nextTick();
		const isValid = performValidation();
		if (isValid) {
			emit("update:options", {
				minItems,
				maxItems,
				defaultValue: arr,
			});
		} else {
			toast.error("Invalid option configuration!");
		}
	}

	async function handleArrayChange(val: any[]) {
		arrayValue.value = val;
		await nextTick();
		const isValid = performValidation();
		if (isValid) {
			emit("update:options", {
				minItems: minItems.value,
				maxItems: maxItems.value,
				defaultValue: arr.value,
			});
		} else {
			toast.error("Invalid option configuration!");
		}
	}

	return isNumeric
		? { value: numericValue, handleChange: handleNumberChange, reset: resetNumber }
		: { value: arrayValue, handleChange: handleArrayChange, reset: resetArray };
}

const { value: minItems, handleChange: handleMinItemsChange, reset: resetMin } = useArrayOption("minItems", true) as NumberRef;
const { value: maxItems, handleChange: handleMaxItemsChange, reset: resetMax } = useArrayOption("maxItems", true) as NumberRef;
const { value: arr, handleChange: handleArrChange, reset: resetArr } = useArrayOption("defaultValue") as StringArrayRef;

const reset = (toProps: boolean = false) => {
	resetMin(toProps);
	resetMax(toProps);
	resetArr(toProps);
};

defineExpose({ reset });
</script>
