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
		<ObjectEditor :obj="obj" @update:obj="handleObjChange" />
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import ObjectEditor from "../ObjectEditor.vue";

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

type StringObjectRef = {
	value: Ref<Record<string, any>, Record<string, any>>;
	handleChange: (val: Record<string, any>) => Promise<void>;
	reset: (toProps?: boolean) => void;
};

function toNumberOrNull(v: any) {
	const n = parseFloat(v);
	return Number.isFinite(n) ? n : null;
}

function performValidation() {
	const min = toNumberOrNull(minItems.value);
	const max = toNumberOrNull(maxItems.value);
	const def = Object.keys(obj.value).length;
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

function useObjectOption(key: string, isNumeric: boolean = false) {
	const numericValue = ref(toNumberOrNull(props.options?.[key]));
	const objectValue = ref<Record<string, any>>(
		typeof props.options?.[key] === "object" && !Array.isArray(props.options?.[key])
			? props.options?.[key]
			: {},
	);

	watch(
		() => props.options?.[key],
		(newVal) => {
			if (isNumeric) {
				numericValue.value = toNumberOrNull(newVal);
			} else {
				objectValue.value = typeof newVal === "object" && !Array.isArray(newVal) ? newVal : {};
			}
		},
	);

	function resetNumber(toProps: boolean) {
		numericValue.value = toProps ? toNumberOrNull(props.options?.[key]) : null;
	}
	function resetObject(toProps: boolean) {
		if (toProps) {
			objectValue.value =
				typeof props.options?.[key] === "object" && !Array.isArray(props.options?.[key])
					? props.options?.[key]
					: {};
		} else {
			objectValue.value = {};
		}
	}

	async function handleNumberChange(val: string) {
		numericValue.value = toNumberOrNull(val);
		await nextTick();
		const isValid = performValidation();
		if (isValid) {
			emit("update:options", {
				minItems,
				maxItems,
				defaultValue: obj.value,
			});
		} else {
			toast.error("Invalid option configuration!");
		}
	}

	async function handleObjectChange(val: Record<string, any>) {
		objectValue.value = val;
		await nextTick();
		const isValid = performValidation();
		if (isValid) {
			emit("update:options", {
				minItems: minItems.value,
				maxItems: maxItems.value,
				defaultValue: obj.value,
			});
		} else {
			toast.error("Invalid option configuration!");
		}
	}

	return isNumeric
		? { value: numericValue, handleChange: handleNumberChange, reset: resetNumber }
		: { value: objectValue, handleChange: handleObjectChange, reset: resetObject };
}

const { value: minItems, handleChange: handleMinItemsChange, reset: resetMin } = useObjectOption("minItems", true) as NumberRef;
const { value: maxItems, handleChange: handleMaxItemsChange, reset: resetMax } = useObjectOption("maxItems", true) as NumberRef;
const { value: obj, handleChange: handleObjChange, reset: resetObj } = useObjectOption("defaultValue") as StringObjectRef;


const reset = (toProps: boolean = false) => {
	resetMin(toProps);
	resetMax(toProps);
	resetObj(toProps);
};

defineExpose({ reset });
</script>
