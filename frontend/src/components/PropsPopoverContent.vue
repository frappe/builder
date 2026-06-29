<template>
	<div
		@click.stop
		@mousedown.stop
		class="props-popover-content flex max-h-80 w-80 flex-col gap-3 overflow-auto rounded-lg bg-surface-base p-4 shadow-lg">
		<div class="flex items-center justify-between gap-2">
			<InlineInput
				label="Label"
				class="w-full"
				:modelValue="label"
				@update:modelValue="(val) => (label = val)"
				placeholder="Enter prop label" />
		</div>
		<div class="flex items-center justify-between gap-2">
			<InlineInput
				label="Key"
				class="w-full"
				:modelValue="computedKey"
				@update:modelValue="(val) => (computedKey = val)"
				placeholder="Enter prop key" />
		</div>
		<div class="flex items-center justify-between gap-2">
			<InlineInput
				label="Type"
				class="w-full"
				type="select"
				:modelValue="standardPropOptions.type"
				@update:modelValue="handleTypeChange"
				:options="propTypes" />
		</div>
		<!-- Disabled for now -->
		<div v-if="false" class="flex items-center justify-between">
			<InputLabel class="w-[88px] shrink-0">Is Required</InputLabel>
			<OptionToggle
				:options="toggleOptions"
				:model-value="String(standardPropOptions.isRequired)"
				@update:model-value="(val) => (standardPropOptions.isRequired = val === 'true')" />
		</div>
		<component
			:is="standardPropTypeComponent"
			:options="standardPropOptions.options || {}"
			ref="optionsComponentRef"
			@update:options="updateStandardPropOptions" />
		<Button
			:disabled="!key.trim().length && !label.trim().length"
			label="Save"
			variant="subtle"
			class="w-full flex-shrink-0"
			@click="save" />
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";

import { computed, nextTick, reactive, ref, watch } from "vue";

import NumberOptions from "@/components/PropsOptions/NumberOptions.vue";
import StringOptions from "@/components/PropsOptions/StringOptions.vue";
import ArrayOptions from "@/components/PropsOptions/ArrayOptions.vue";
import ObjectOptions from "@/components/PropsOptions/ObjectOptions.vue";
import BooleanOptions from "@/components/PropsOptions/BooleanOptions.vue";
import SelectOptions from "@/components/PropsOptions/SelectOptions.vue";

import { toKebabCase } from "@/utils/helpers";
import ColorOptions from "./PropsOptions/ColorOptions.vue";
import ImageOptions from "./PropsOptions/ImageOptions.vue";
import InlineInput from "./Controls/InlineInput.vue";

const props = withDefaults(
	defineProps<{
		mode: "add" | "edit";
		propName?: string | null;
		propDetails?: BlockProps[string] | null;
		closePopover?: () => void;
	}>(),
	{
		mode: "add",
	},
);

const STANDARD_PROP_TYPES = [
	"string",
	"number",
	"boolean",
	"select",
	"array",
	"object",
	"image",
	"color",
] as const;
const COMPONENT_MAPPING = {
	string: StringOptions,
	number: NumberOptions,
	boolean: BooleanOptions,
	select: SelectOptions,
	array: ArrayOptions,
	object: ObjectOptions,
	image: ImageOptions,
	color: ColorOptions,
} as const;

const TOGGLE_OPTIONS: { label: string; value: string }[] = [
	{ label: "Yes", value: "true" },
	{ label: "No", value: "false" },
];

const label = ref(props.propDetails?.label ?? "");
const key = ref(props.propName ?? "");
const standardPropOptions = reactive<BlockPropOptions>(getInitialStandardPropOptions());
const standardPropDependencyMap = reactive<{ [key: string]: any }>(getInitialDependencies());
const optionsComponentRef = ref<any>(null);

const emit = defineEmits({
	"add:prop": ({ name, value }: { name: string; value: BlockProps[string] }) => true,
	"update:prop": ({
		oldPropName,
		newName,
		newValue,
	}: {
		oldPropName: string;
		newName: string;
		newValue: BlockProps[string];
	}) => true,
});

const computedKey = computed({
	get: () => (key.value ? key.value : toKebabCase(label.value).replaceAll("-", "_")),
	set: (val) => {
		key.value = val;
	},
});

const toggleOptions = computed(() => TOGGLE_OPTIONS);

const propTypes = computed(() => getStandardPropTypes());

const standardPropTypeComponent = computed(() => {
	return COMPONENT_MAPPING[standardPropOptions.type as keyof typeof COMPONENT_MAPPING];
});

function getInitialStandardPropOptions(): BlockPropOptions {
	if (props.propDetails?.propOptions) {
		return {
			...props.propDetails.propOptions,
			isRequired: Boolean(props.propDetails.propOptions?.isRequired),
			type: props.propDetails.propOptions?.type || "string",
		};
	}

	return {
		isRequired: false,
		type: "string",
		options: {},
		dependencies: {},
	};
}

function getInitialDependencies() {
	return props.propDetails?.propOptions?.dependencies || {};
}

function getStandardPropTypes() {
	return [
		{ label: "String", value: "string" },
		{ label: "Number", value: "number" },
		{ label: "Boolean", value: "boolean" },
		{ label: "Select", value: "select" },
		{ label: "Array", value: "array" },
		{ label: "Object", value: "object" },
		{ label: "Image", value: "image" },
		{ label: "Color", value: "color" },
	];
}

function isValidStandardPropType(
	type: string,
): type is "string" | "number" | "boolean" | "select" | "array" | "object" {
	return STANDARD_PROP_TYPES.includes(type as any);
}

function setPropType(type: string) {
	if (isValidStandardPropType(type)) {
		standardPropOptions.type = type;
	}
}

const handleTypeChange = async (newVal: string) => {
	setPropType(newVal);
	await nextTick();
	resetState({ keepName: true, keepProps: false, keepType: true });
};

const updateStandardPropOptions = (options: any) => {
	standardPropOptions.options = options;
};

interface ResetParams {
	keepName: boolean;
	keepProps: boolean;
	keepType: boolean;
}

function resetStandardState(keepProps: boolean, keepType: boolean) {
	const details = keepProps ? props.propDetails : null;

	if (details?.propOptions) {
		const nextType = keepType ? standardPropOptions.type : (details.propOptions?.type ?? "string");

		Object.assign(standardPropOptions, {
			...details.propOptions,
			isRequired: Boolean(details.propOptions?.isRequired),
			type: nextType,
		});

		updateDependencyMap(details.propOptions?.dependencies || {});
	} else {
		if (!keepType) {
			standardPropOptions.type = "string";
		}

		Object.assign(standardPropOptions, {
			isRequired: false,
			type: standardPropOptions.type,
			options: {},
			dependencies: {},
		});

		updateDependencyMap({});
	}
}

function updateDependencyMap(deps: { [key: string]: any }) {
	Object.keys(standardPropDependencyMap).forEach((k) => delete standardPropDependencyMap[k]);
	Object.assign(standardPropDependencyMap, deps);
}

const resetState = async (params: ResetParams) => {
	const { keepName, keepProps, keepType } = params;
	const details = keepProps ? props.propDetails : null;

	if (!keepName) {
		key.value = props.propName ?? "";
		label.value = details?.label ?? "";
	}

	resetStandardState(keepProps, keepType);

	optionsComponentRef.value?.reset(!!keepProps);
};

function buildPropValue(): BlockProps[string] {
	return {
		label: label.value,
		isStandard: true,
		isDynamic: false,
		isPassedDown: true,
		comesFrom: null,
		value: null,
		propOptions: {
			...standardPropOptions,
			dependencies: standardPropDependencyMap,
		},
	};
}

const save = async () => {
	await nextTick();
	const propValue = buildPropValue();

	if (props.mode === "add") {
		emit("add:prop", { name: computedKey.value, value: propValue });
	} else {
		emit("update:prop", {
			oldPropName: props.propName!,
			newName: computedKey.value,
			newValue: propValue,
		});
	}
};

watch(
	[() => props.propName, () => props.propDetails],
	() => resetState({ keepName: false, keepProps: true, keepType: false }),
	{ immediate: true, deep: true },
);

defineExpose({ reset: resetState });
</script>
