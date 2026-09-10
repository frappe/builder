<template>
	<div v-if="false" class="flex items-center justify-between">
		<InlineInput
			:label="__('Min. Items')"
			:modelValue="minItems"
			@update:modelValue="handleMinItemsChange"
			@input="handleMinItemsChange"
			:placeholder="__('Enter min number of items')"></InlineInput>
	</div>
	<div v-if="false" class="flex items-center justify-between">
		<InlineInput
			:label="__('Max. Items')"
			:modelValue="maxItems"
			@update:modelValue="handleMaxItemsChange"
			@input="handleMaxItemsChange"
			:placeholder="__('Enter max number of items')"></InlineInput>
	</div>
	<div class="flex items-center justify-between">
		<InlineInput
			:label="__('Item Type')"
			class="w-full"
			type="select"
			:options="[
				{ label: __('Text'), value: 'string' },
				{ label: __('Image'), value: 'image' },
			]"
			:modelValue="itemType"
			@update:modelValue="handleItemTypeChange"></InlineInput>
	</div>
	<div class="flex flex-col gap-3">
		<InputLabel class="w-[88px] shrink-0">{{ __("Default Items") }}</InputLabel>
		<ArrayEditor :arr :itemType @update:arr="handleArrChange" />
	</div>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import ArrayEditor from "@/components/ArrayEditor.vue";
import { nextTick, ref, watch } from "vue";
import { Ref } from "vue";
import { toast } from "frappe-ui";
import InlineInput from "../Controls/InlineInput.vue";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

const itemType = ref<"string" | "image">(props.options?.itemType === "image" ? "image" : "string");

watch(
	() => props.options?.itemType,
	(newVal) => {
		itemType.value = newVal === "image" ? "image" : "string";
	},
);

type NumberRef = {
	value: Ref<number | null, number | null>;
	handleChange: (val: string) => Promise<void>;
	reset: (toProps?: boolean) => void;
};

type StringArrayRef = {
	value: Ref<ArrayPropItem[], ArrayPropItem[]>;
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
	const arrayValue = ref<ArrayPropItem[]>(Array.isArray(props.options?.[key]) ? props.options?.[key] : []);

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
				minItems: minItems.value,
				maxItems: maxItems.value,
				defaultValue: arr.value,
				itemType: itemType.value,
			});
		} else {
			toast.error(__("Invalid option configuration!"));
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
				itemType: itemType.value,
			});
		} else {
			toast.error(__("Invalid option configuration!"));
		}
	}

	return isNumeric
		? { value: numericValue, handleChange: handleNumberChange, reset: resetNumber }
		: { value: arrayValue, handleChange: handleArrayChange, reset: resetArray };
}

const {
	value: minItems,
	handleChange: handleMinItemsChange,
	reset: resetMin,
} = useArrayOption("minItems", true) as NumberRef;
const {
	value: maxItems,
	handleChange: handleMaxItemsChange,
	reset: resetMax,
} = useArrayOption("maxItems", true) as NumberRef;
const {
	value: arr,
	handleChange: handleArrChange,
	reset: resetArr,
} = useArrayOption("defaultValue") as StringArrayRef;

const handleItemTypeChange = async (val: "string" | "image") => {
	itemType.value = val;
	arr.value = [];
	await nextTick();
	emit("update:options", {
		minItems: minItems.value,
		maxItems: maxItems.value,
		defaultValue: [],
		itemType: val,
	});
};

const reset = (toProps: boolean = false) => {
	resetMin(toProps);
	resetMax(toProps);
	resetArr(toProps);
	itemType.value = toProps && props.options?.itemType === "image" ? "image" : "string";
};

defineExpose({ reset });
</script>
