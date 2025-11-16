<template>
	<div class="flex flex-col gap-3">
		<InputLabel>Options</InputLabel>
		<ArrayEditor :arr="options" @update:arr="handleOptionsChange" />
	</div>
	<div class="flex items-center justify-between">
		<InputLabel>Default Value</InputLabel>
		<Input type="select" :options="optionsAvailable" @update:model-value="handleDefaultValueChange" placeholder="Select default value"></Input>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import ArrayEditor from "@/components/ArrayEditor.vue";
import { computed, nextTick, Ref, ref, watch } from "vue";

const props = defineProps<{
	options: Record<string, any>;
}>();

const emit = defineEmits<{
	(update: "update:options", value: Record<string, any>): void;
}>();

type StringRef = {
	value: Ref<string | null, string | null>;
	handleChange: (val: string) => Promise<void>;
	reset: (toProps?: boolean) => void;
};

type StringArrayRef = {
	value: Ref<string[], string[]>;
	handleChange: (val: any[]) => Promise<void>;
	reset: (toProps?: boolean) => void;
};

function useSelectOption(key: string, isString: boolean = false) {
	const stringValue = ref(props.options?.[key]);
	const arrayValue = ref<string[]>(Array.isArray(props.options?.[key]) ? props.options?.[key] : []);

	watch(
		() => props.options?.[key],
		(newVal) => {
			if (isString) {
				stringValue.value = newVal;
			} else {
				arrayValue.value = Array.isArray(newVal) ? newVal : [];
			}
		},
	);

	function resetString(toProps: boolean) {
		stringValue.value = toProps ? props.options?.[key] : "";
	}
	function resetArray(toProps: boolean) {
		arrayValue.value = toProps && Array.isArray(props.options?.[key]) ? props.options?.[key] : [];
	}

	async function handleStringChange(val: string) {
		stringValue.value = val;
		emit("update:options", {});
	}

	async function handleArrayChange(val: any[]) {
		arrayValue.value = val;
		await nextTick();
		emit("update:options", {});
	}

	return isString
		? { value: stringValue, handleChange: handleStringChange, reset: resetString }
		: { value: arrayValue, handleChange: handleArrayChange, reset: resetArray };
}

const {
	value: options,
	handleChange: handleOptionsChange,
	reset: resetOptions,
} = useSelectOption("options") as StringArrayRef;
const {
	value: defaultValue,
	handleChange: handleDefaultValueChange,
	reset: resetDefaultValue,
} = useSelectOption("defaultValue", true) as StringRef;

const optionsAvailable = computed(() => {
	return options.value.map((opt) => ({ label: opt, value: opt }));
});

const reset = (toProps: boolean = false) => {
	resetOptions(toProps);
	resetDefaultValue(toProps);
};

defineExpose({ reset });
</script>
