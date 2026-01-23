<template>
	<div
		@click.stop
		@mousedown.stop
		class="props-popover-content flex max-h-80 w-80 flex-col gap-3 overflow-auto rounded-lg bg-surface-white p-4 shadow-lg">
		<div v-if="showIsStandardInput" class="flex items-center justify-between">
			<InputLabel>Is Standard</InputLabel>
			<OptionToggle
				:options="toggleOptions"
				:model-value="isStandard"
				@update:model-value="handleIsStandardChange" />
		</div>
		<div v-if="isStandardBool" class="flex items-center justify-between">
			<InputLabel>Label</InputLabel>
			<Input
				v-model="label"
				placeholder="Enter prop label"
				@update:model-value="(val) => (label = val)"
				@input="(val) => (label = val)"></Input>
		</div>
		<div class="flex items-center justify-between">
			<InputLabel>Key</InputLabel>
			<Input
				v-model="key"
				:placeholder="computedKey || 'Enter prop key'"
				@update:model-value="(val) => (key = val)"
				@input="(val) => (key = val)"></Input>
		</div>
		<div class="flex items-center justify-between">
			<InputLabel>Type</InputLabel>
			<Input
				placeholder="Select prop type"
				type="select"
				:options="propTypes"
				:model-value="selectedPropType"
				@update:model-value="handleTypeChange"></Input>
		</div>
		<div v-if="!isStandardBool" class="flex items-center justify-between">
			<InputLabel v-model="value">Value</InputLabel>
			<Input
				v-if="isStaticProp"
				v-model="value"
				placeholder="Enter prop value"
				@update:model-value="(val) => (value = val)"
				@input="(val) => (value = val)"></Input>
			<Autocomplete
				v-else
				anchorSelector=".props-popover-content"
				class="w-full [&>.form-input]:border-none [&>.form-input]:hover:border-none"
				ref="autoCompleteRef"
				placeholder="Choose prop value"
				:allow-arbitrary-value="false"
				:modelValue="value"
				:getOptions="getOptions"
				@update:modelValue="handleValueSelection" />
		</div>
		<div v-if="!isStandardBool" class="flex items-center justify-between">
			<InputLabel>Pass Down</InputLabel>
			<OptionToggle
				:options="toggleOptions"
				:model-value="isPassedDown"
				@update:model-value="(val) => (isPassedDown = val)" />
		</div>
		<!-- Disabled for now-->
		<div v-if="false && !isStandardBool && isInFragmentMode" class="flex items-center justify-between">
			<InputLabel>Is Editable</InputLabel>
			<OptionToggle
				:options="toggleOptions"
				:model-value="isEditable"
				@update:model-value="(val) => (isEditable = val)" />
		</div>
		<template v-if="isStandardBool">
			<!-- Disabled for now -->
			<div v-if="false" class="flex items-center justify-between">
				<InputLabel>Is Required</InputLabel>
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
		</template>
		<BuilderButton
			:disabled="!key.trim().length && !label.trim().length"
			label="Save"
			variant="subtle"
			class="w-full flex-shrink-0"
			@click="save" />
	</div>
</template>

<script setup lang="ts">
import Block from "@/block";

import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import Autocomplete from "@/components/Controls/Autocomplete.vue";

import { computed, nextTick, reactive, ref, watch } from "vue";

import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";

import NumberOptions from "@/components/PropsOptions/NumberOptions.vue";
import StringOptions from "@/components/PropsOptions/StringOptions.vue";
import ArrayOptions from "@/components/PropsOptions/ArrayOptions.vue";
import ObjectOptions from "@/components/PropsOptions/ObjectOptions.vue";
import BooleanOptions from "@/components/PropsOptions/BooleanOptions.vue";
import SelectOptions from "@/components/PropsOptions/SelectOptions.vue";

import { getDataArray, toKebabCase } from "@/utils/helpers";
import useBlockDataStore from "@/stores/blockDataStore";
import ColorOptions from "./PropsOptions/ColorOptions.vue";
import ImageOptions from "./PropsOptions/ImageOptions.vue";

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

const canvasStore = useCanvasStore();
const blockDataStore = useBlockDataStore();

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

const isStandard = ref(props.propDetails?.isStandard ? "true" : "false");
const isEditable = ref("false");
const isPassedDown = ref(props.propDetails?.isPassedDown ? "true" : "false");
const label = ref(props.propDetails?.label ?? "");
const key = ref(props.propName ?? "");
const value = ref(props.propDetails?.value ?? "");
const comesFrom = ref<BlockProps[string]["comesFrom"]>(props.propDetails?.comesFrom ?? null);
const selectedNonStandardPropType = ref(getInitialNonStandardPropType());
const standardPropOptions = reactive<BlockPropsStandardOptions>(getInitialStandardPropOptions());
const standardPropDependencyMap = reactive<{ [key: string]: any }>(getInitialDependencies());
const autoCompleteRef = ref<typeof Autocomplete | null>(null);
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

const isStandardBool = computed(() => isStandard.value === "true");
const isInFragmentMode = computed(() => canvasStore.editingMode == "fragment");
const isStaticProp = computed(() => selectedNonStandardPropType.value === "static");

const showIsStandardInput = computed(() => {
	return isInFragmentMode.value && !blockController.getFirstSelectedBlock()?.getParentBlock();
});

const toggleOptions = computed(() => TOGGLE_OPTIONS);

const propTypes = computed(() => {
	return isStandardBool.value ? getStandardPropTypes() : getNonStandardPropTypes();
});

const selectedPropType = computed(() => {
	return isStandardBool.value ? standardPropOptions.type : selectedNonStandardPropType.value;
});

const standardPropTypeComponent = computed(() => {
	return COMPONENT_MAPPING[standardPropOptions.type as keyof typeof COMPONENT_MAPPING];
});

const currentBlock = computed(() => blockController.getFirstSelectedBlock());

const pageDataArray = computed(() => {
	if (currentBlock.value) {
		return getDataArray(blockDataStore.getPageData(currentBlock.value.blockId) || {});
	}
	return [];
});

const blockDataArray = computed(() => {
	if (currentBlock.value) {
		return getDataArray(blockDataStore.getBlockData(currentBlock.value.blockId, "passedDown") || {});
	}
	return [];
});

function getInitialNonStandardPropType() {
	return props.propDetails && !props.propDetails.isStandard
		? props.propDetails.isDynamic
			? "dynamic"
			: "static"
		: "static";
}

function getInitialStandardPropOptions(): BlockPropsStandardOptions {
	if (props.propDetails?.isStandard) {
		return {
			...props.propDetails.standardOptions,
			isRequired: Boolean(props.propDetails.standardOptions?.isRequired),
			type: props.propDetails.standardOptions?.type || "string",
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
	return props.propDetails?.isStandard ? props.propDetails.standardOptions?.dependencies || {} : {};
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

function getNonStandardPropTypes() {
	return [
		{ label: "Static", value: "static" },
		{ label: "Dynamic", value: "dynamic" },
	];
}

function isValidStandardPropType(
	type: string,
): type is "string" | "number" | "boolean" | "select" | "array" | "object" {
	return STANDARD_PROP_TYPES.includes(type as any);
}

function setPropType(type: string) {
	if (isStandardBool.value && isValidStandardPropType(type)) {
		standardPropOptions.type = type;
	} else {
		selectedNonStandardPropType.value = type as "static" | "dynamic";
	}
	comesFrom.value = null;
	value.value = "";
}

function filterDataOptions(dataArray: string[], query: string) {
	return dataArray
		.filter((prop) => query.trim() === "" || prop.toLowerCase().includes(query.toLowerCase()))
		.map((prop) => ({ label: prop, value: prop }));
}

const getOptions = async (query: string) => {
	const pageOptions = filterDataOptions(pageDataArray.value, query).map((opt) => ({
		...opt,
		value: `${opt.value}--dataScript`,
	}));

	const blockOptions = filterDataOptions(blockDataArray.value, query).map((opt) => ({
		...opt,
		value: `${opt.value}--blockDataScript`,
	}));

	return [...pageOptions, ...blockOptions];
};

const handleIsStandardChange = async (newVal: string) => {
	isStandard.value = newVal;
	await nextTick();
	resetState({ keepName: true, keepIsStandard: true, keepProps: false, keepType: false });
};

const handleTypeChange = async (newVal: string) => {
	setPropType(newVal);
	await nextTick();
	resetState({ keepName: true, keepIsStandard: true, keepProps: false, keepType: true });
};

const handleValueSelection = (option: string | null) => {
	if (option) {
		const parts = option.split("--");
		comesFrom.value = parts[parts.length - 1] as BlockProps[string]["comesFrom"];
		value.value = parts.slice(0, -1).join("--");
	} else {
		comesFrom.value = null;
		value.value = "";
	}
};

const updateStandardPropOptions = (options: any) => {
	standardPropOptions.options = options;
};

interface ResetParams {
	keepName: boolean;
	keepIsStandard: boolean;
	keepProps: boolean;
	keepType: boolean;
}

function getDefaultIsStandard(keepProps: boolean): string {
	const isStandardByDefault = isInFragmentMode.value && props.mode === "add";
	const propDetailsStandard = keepProps ? props.propDetails?.isStandard : undefined;
	return propDetailsStandard !== undefined
		? String(propDetailsStandard)
		: isStandardByDefault
		? "true"
		: "false";
}

function resetNonStandardState(keepProps: boolean, keepType: boolean) {
	if (!keepType) {
		const details = keepProps ? props.propDetails : null;
		selectedNonStandardPropType.value = details?.isDynamic ? "dynamic" : "static";
	}
}

function resetStandardState(keepProps: boolean, keepType: boolean) {
	const details = keepProps ? props.propDetails : null;

	if (details?.isStandard) {
		const nextType = keepType ? standardPropOptions.type : details.standardOptions?.type ?? "string";

		Object.assign(standardPropOptions, {
			...details.standardOptions,
			isRequired: Boolean(details.standardOptions?.isRequired),
			type: nextType,
		});

		updateDependencyMap(details.standardOptions?.dependencies || {});
	} else if (isStandardBool.value) {
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
	const { keepName, keepIsStandard, keepProps, keepType } = params;
	const details = keepProps ? props.propDetails : null;

	if (!keepName) {
		key.value = props.propName ?? "";
		label.value = details?.label ?? "";
	}

	if (!keepIsStandard) {
		isStandard.value = getDefaultIsStandard(keepProps);
	}

	value.value = details?.value ?? "";

	if (isStandardBool.value) {
		resetStandardState(keepProps, keepType);
	} else {
		resetNonStandardState(keepProps, keepType);
	}

	optionsComponentRef.value?.reset(!!keepProps);
};

function buildPropValue(): BlockProps[string] {
	return {
		label: label.value,
		isStandard: isStandardBool.value,
		isDynamic: isStandardBool.value ? false : selectedNonStandardPropType.value === "dynamic",
		isPassedDown: isStandardBool.value || isPassedDown.value === "true",
		comesFrom: comesFrom.value,
		value: isStandardBool.value ? null : value.value,
		standardOptions: isStandardBool.value
			? {
					...standardPropOptions,
					dependencies: standardPropDependencyMap.value,
			  }
			: undefined,
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
	() => resetState({ keepName: false, keepIsStandard: false, keepProps: true, keepType: false }),
	{ immediate: true, deep: true },
);

watch(selectedPropType, () => autoCompleteRef.value?.refreshOptions(), { immediate: true });

defineExpose({ reset: resetState });
</script>
