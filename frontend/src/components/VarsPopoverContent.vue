<template>
	<div
		@click.stop
		@mousedown.stop
		class="vars-popover-content flex max-h-80 w-80 flex-col gap-3 overflow-auto rounded-lg bg-surface-base p-4 shadow-lg">
		<div class="flex items-center justify-between gap-2">
			<InlineInput
				label="Name"
				class="w-full"
				:modelValue="name"
				@update:modelValue="(val) => (name = val)"
				placeholder="Enter variable name" />
		</div>
		<div class="flex items-center justify-between gap-2">
			<InlineInput
				label="Type"
				class="w-full"
				type="select"
				:modelValue="type"
				@update:modelValue="handleTypeChange"
				:options="varTypes" />
		</div>
		<div v-if="type === 'boolean'" class="flex items-center justify-between gap-2">
			<InputLabel class="w-1/3 min-w-[88px] shrink-0">Initial Value</InputLabel>
			<OptionToggle
				:options="toggleOptions"
				:model-value="String(initialValue)"
				@update:model-value="(val) => (initialValue = val === 'true')" />
		</div>
		<div v-else-if="type === 'number'" class="flex items-center justify-between gap-2">
			<InputLabel class="w-1/3 min-w-[88px] shrink-0">Initial Value</InputLabel>
			<Input
				type="number"
				class="w-full"
				:modelValue="String(initialValue ?? '')"
				@update:model-value="(val) => (initialValue = val === '' ? 0 : Number(val))"
				placeholder="Enter initial value" />
		</div>
		<div v-else-if="type === 'string'" class="flex items-center justify-between gap-2">
			<InputLabel class="w-1/3 min-w-[88px] shrink-0">Initial Value</InputLabel>
			<Input
				class="w-full"
				:modelValue="String(initialValue ?? '')"
				@update:model-value="(val) => (initialValue = val)"
				placeholder="Enter initial value" />
		</div>
		<ArrayOptions v-else-if="type === 'array'" :options="arrayOptions" @update:options="updateArrayOptions" />
		<ObjectOptions
			v-else-if="type === 'object'"
			:options="objectOptions"
			@update:options="updateObjectOptions" />
		<Button
			:disabled="!name.trim().length"
			label="Save"
			variant="subtle"
			class="w-full flex-shrink-0"
			@click="save" />
	</div>
</template>

<script setup lang="ts">
import ArrayOptions from "@/components/PropsOptions/ArrayOptions.vue";
import ObjectOptions from "@/components/PropsOptions/ObjectOptions.vue";
import Input from "@/components/Controls/Input.vue";
import InputLabel from "@/components/Controls/InputLabel.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
// import { getDefaultInitialValue, isValidVarName } from "@/utils/componentVars";
import { computed, ref, watch } from "vue";
import { toast } from "frappe-ui";

const props = defineProps<{
	mode: "add" | "edit";
	varName?: string | null;
	varDetails?: BlockVars[string] | null;
}>();

const emit = defineEmits({
	"add:var": ({ name, value }: { name: string; value: BlockVars[string] }) => true,
	"update:var": ({
		oldVarName,
		newName,
		newValue,
	}: {
		oldVarName: string;
		newName: string;
		newValue: BlockVars[string];
	}) => true,
});

const toggleOptions = [
	{ label: "True", value: "true" },
	{ label: "False", value: "false" },
];

const varTypes = [
	{ label: "Number", value: "number" },
	{ label: "String", value: "string" },
	{ label: "Boolean", value: "boolean" },
	{ label: "Object", value: "object" },
	{ label: "Array", value: "array" },
];

const name = ref(props.varName ?? "");
const type = ref<BlockVarType>(props.varDetails?.type ?? "number");
const initialValue = ref<BlockVars[string]["initialValue"]>(
	props.varDetails?.initialValue ?? getDefaultInitialValue(type.value),
);

const arrayOptions = computed(() => ({
	defaultValue: Array.isArray(initialValue.value) ? initialValue.value : [],
}));

const objectOptions = computed(() => ({
	defaultValue:
		typeof initialValue.value === "object" &&
		initialValue.value !== null &&
		!Array.isArray(initialValue.value)
			? initialValue.value
			: {},
}));

function handleTypeChange(value: BlockVarType) {
	type.value = value;
	initialValue.value = getDefaultInitialValue(value);
}

function updateArrayOptions(options: Record<string, any>) {
	initialValue.value = options.defaultValue ?? [];
}

function updateObjectOptions(options: Record<string, any>) {
	initialValue.value = options.defaultValue ?? {};
}

function buildVarValue(): BlockVars[string] {
	return {
		type: type.value,
		initialValue: initialValue.value ?? getDefaultInitialValue(type.value),
	};
}

function save() {
	const computedName = name.value.trim();
	if (!isValidVarName(computedName)) {
		toast.error("Use a valid JavaScript identifier that is not reserved");
		return;
	}

	const value = buildVarValue();
	if (props.mode === "add") {
		emit("add:var", { name: computedName, value });
		return;
	}

	emit("update:var", {
		oldVarName: props.varName as string,
		newName: computedName,
		newValue: value,
	});
}

interface ResetParams {
	keepName: boolean;
	keepProps: boolean;
	keepType: boolean;
}

function resetState(params: ResetParams) {
	const { keepName, keepProps, keepType } = params;
	const details = keepProps ? props.varDetails : null;

	if (!keepName) {
		name.value = props.varName ?? "";
	}

	if (details) {
		if (!keepType) {
			type.value = details.type ?? "number";
		}
		initialValue.value = details.initialValue ?? getDefaultInitialValue(type.value);
	} else {
		if (!keepType) {
			type.value = "number";
		}
		initialValue.value = getDefaultInitialValue(type.value);
	}
}

function getDefaultInitialValue(type: BlockVarType) {
	switch (type) {
		case "number":
			return 0;
		case "string":
			return "";
		case "boolean":
			return false;
		case "object":
			return {};
		case "array":
			return [];
		default:
			return "";
	}
}

function isValidVarName(name: string) {
	return /^[a-zA-Z][a-zA-Z0-9]*$/.test(name);
}

watch(
	() => [props.varName, props.varDetails],
	() => resetState({ keepName: false, keepProps: true, keepType: false }),
	{ immediate: true, deep: true },
);

defineExpose({ reset: resetState });
</script>
