<template>
	<div
		@click.stop
		@mousedown.stop
		class="props-popover-content flex max-h-80 w-80 flex-col gap-3 overflow-auto rounded-lg bg-surface-white p-4 shadow-lg">
		<div v-if="showIsStandardInput" class="flex items-center justify-between">
			<InputLabel>Is Standard</InputLabel>
			<OptionToggle
				:options="[
					{
						label: 'Yes',
						value: 'true',
					},
					{
						label: 'No',
						value: 'false',
					},
				]"
				:model-value="isStandard"
				@update:model-value="handleIsStandardChange" />
		</div>
		<div class="flex items-center justify-between">
			<InputLabel>Name</InputLabel>
			<Input
				v-model="name"
				placeholder="Enter prop name"
				@update:model-value="
					(val) => {
						name = val;
					}
				"
				@input="
					(val) => {
						name = val;
					}
				"></Input>
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
				v-if="selectedPropType == 'static'"
				v-model="value"
				placeholder="Enter prop name"
				@update:model-value="
					(val) => {
						value = val;
					}
				"
				@input="
					(val) => {
						value = val;
					}
				"></Input>
			<Autocomplete
				v-else
				:make-fixed="true"
				fix-to=".props-popover-content"
				class="w-full [&>.form-input]:border-none [&>.form-input]:hover:border-none"
				ref="autoCompleteRef"
				placeholder="Choose prop value"
				:allow-arbitrary-value="false"
				:modelValue="value"
				:getOptions="getOptions"
				@update:modelValue="handleValueSelection" />
		</div>
		<!-- Disabled for now-->
		<div v-if="false && !isStandardBool && isInFragmentMode" class="flex items-center justify-between">
			<InputLabel>Is Editable</InputLabel>
			<OptionToggle
				:options="[
					{
						label: 'Yes',
						value: 'true',
					},
					{
						label: 'No',
						value: 'false',
					},
				]"
				:model-value="isEditable"
				@update:model-value="(val) => (isEditable = val)" />
		</div>
		<template v-if="isStandardBool">
			<div class="flex items-center justify-between">
				<InputLabel>Is Required</InputLabel>
				<OptionToggle
					:options="[
						{
							label: 'Yes',
							value: 'true',
						},
						{
							label: 'No',
							value: 'false',
						},
					]"
					:model-value="String(standardPropOptions.isRequired)"
					@update:model-value="(val) => (standardPropOptions.isRequired = val === 'true')" />
			</div>
			<component
				:is="componentMapping[standardPropOptions.type as keyof typeof componentMapping]"
				:options="standardPropOptions.options || {}"
				ref="optionsComponentRef"
				@update:options="(options: any) => {
					standardPropOptions.options = options;
				}" />
		</template>
		<BuilderButton label="Save" variant="subtle" class="w-full flex-shrink-0" @click="save" />
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

import usePageStore from "@/stores/pageStore";
import { getCollectionKeys, getDataArray, getStandardPropValue } from "@/utils/helpers";

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

const isStandard = ref(props.propDetails?.isStandard ? "true" : "false");
const isStandardBool = computed(() => isStandard.value === "true");
const isEditable = ref("false"); // TODO: required?
const name = ref(props.propName ?? "");
const value = ref(props.propDetails?.value ?? "");
const comesFrom = ref<BlockProps[string]["comesFrom"]>(props.propDetails?.comesFrom ?? null);
const selectedNonStandardPropType = ref(
	props.propDetails && !props.propDetails.isStandard ? !props.propDetails.isDynamic : "static",
);
const standardPropOptions = reactive<BlockPropsStandardOptions>(
	props.propDetails && props.propDetails.isStandard
		? {
				...props.propDetails.standardOptions,
				isRequired: Boolean(props.propDetails.standardOptions?.isRequired),
				type: props.propDetails.standardOptions?.type || "string",
		  }
		: {
				isRequired: false,
				type: "string",
				// defaultValue: "",
				options: {},
				dependencies: {},
		  },
);
const standardPropDependencyMap = reactive<{ [key: string]: any }>(
	props.propDetails && props.propDetails.isStandard
		? props.propDetails.standardOptions?.dependencies || {}
		: {},
);
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

const propTypes = computed(() => {
	if (isStandardBool.value) {
		return [
			{
				label: "String",
				value: "string",
			},
			{
				label: "Number",
				value: "number",
			},
			{
				label: "Boolean",
				value: "boolean",
			},
			{
				label: "Select",
				value: "select",
			},
			{
				label: "Array",
				value: "array",
			},
			{
				label: "Object",
				value: "object",
			},
		];
	} else {
		return [
			{
				label: "Static",
				value: "static",
			},
			{
				label: "Dynamic",
				value: "dynamic",
			},
		];
	}
});

const showIsStandardInput = computed(() => {
	return canvasStore.editingMode == "fragment" && !blockController.getFirstSelectedBlock()?.getParentBlock();
});

const isInFragmentMode = computed(() => {
	return canvasStore.editingMode == "fragment";
});

const selectedPropType = computed(() => {
	if (isStandardBool.value) {
		return standardPropOptions.type;
	} else {
		return selectedNonStandardPropType.value;
	}
});

const STANDARD_PROP_TYPES = ["string", "number", "boolean", "select", "array", "object"];

const setPropType = (type: string) => {
	if (isStandardBool.value && STANDARD_PROP_TYPES.includes(type)) {
		standardPropOptions.type = type as "string" | "number" | "boolean" | "select" | "array" | "object";
	} else {
		selectedNonStandardPropType.value = type as "static" | "dynamic";
	}
	comesFrom.value = null;
	value.value = "";
};

const pageDataArray = computed(() => {
	return getDataArray(blockController.getFirstSelectedBlock(), usePageStore().pageData, "dataScript");
});

const blockDataArray = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (currentBlock) {
		return getDataArray(currentBlock, currentBlock.getBlockData("passedDown"), "blockDataScript");
	}
	return [];
});

const defaultProps = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	const isCurrentBlockInRepeater = currentBlock?.isInsideRepeater();
	const repeaterRoot = isCurrentBlockInRepeater ? currentBlock?.getRepeaterParent() : null;
	if (repeaterRoot) {
		const key = repeaterRoot.getDataKey("key");
		const comesFrom = repeaterRoot.getDataKey("comesFrom");
		if (key && comesFrom === "props") {
			const componentRoot = blockController.getComponentRootBlock(repeaterRoot);
			const parsedValue = getStandardPropValue(key, componentRoot)?.value;
			if (!parsedValue) return {};
			if (Array.isArray(parsedValue)) {
				return {
					item: {
						value: parsedValue[0],
						isStandard: false,
						type: "static",
					},
				};
			} else if (typeof parsedValue === "object") {
				return {
					key: {
						value: Object.keys(parsedValue)[0],
						isStandard: false,
						type: "static",
					},
					value: {
						value: parsedValue[Object.keys(parsedValue)[0]],
						isStandard: false,
						type: "static",
					},
				};
			}
		}
	}
	return {};
});

const getParentProps = (baseBlock: Block, baseProps: string[]): string[] => {
	const parentBlock = baseBlock.getParentBlock();
	if (parentBlock) {
		// TODO: disallow array and obj props from parent blocks
		const parentProps: string[] = Object.keys(parentBlock.getBlockProps()).map((key) => key);
		const combinedProps = [...baseProps, ...parentProps].reduce((acc, prop) => {
			if (!acc.find((p: string) => p === prop)) {
				acc.push(prop);
			}
			return acc;
		}, [] as string[]);
		return getParentProps(parentBlock, combinedProps);
	} else {
		return baseProps;
	}
};

const getOptions = async (query: string) => {
	let options: { label: string; value: string }[] = [];
	getParentProps(blockController.getFirstSelectedBlock()!, []).map((prop) => {
		if (prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--props`,
			});
		}
	});
	Object.keys(defaultProps.value || {}).map((prop) => {
		if (prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--props`,
			});
		}
	});
	pageDataArray.value.map((prop) => {
		if (prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--dataScript`,
			});
		}
	});
	blockDataArray.value.map((prop) => {
		if (prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--blockDataScript`,
			});
		}
	});

	return options;
};

const componentMapping = {
	string: StringOptions,
	number: NumberOptions,
	boolean: BooleanOptions,
	select: SelectOptions,
	array: ArrayOptions,
	object: ObjectOptions,
};

const handleIsStandardChange = async (newVal: string) => {
	isStandard.value = newVal;
	await nextTick();
	reset({
		keepName: true,
		keepIsStandard: true,
		keepProps: false,
		keepType: false,
	});
};

const handleTypeChange = async (newVal: string) => {
	setPropType(newVal);
	await nextTick();
	reset({
		keepName: true,
		keepIsStandard: true,
		keepProps: false,
		keepType: true,
	});
};

const handleValueSelection = (option: string | null) => {
	if (option) {
		comesFrom.value = option.split("--").slice(-1)[0] as BlockProps[string]["comesFrom"];
		value.value = option.split("--").slice(0, -1).join("--");
	} else {
		comesFrom.value = null;
		value.value = "";
	}
};

const reset = async (keepParams: {
	keepName: boolean;
	keepIsStandard: boolean;
	keepProps: boolean;
	keepType: boolean;
}) => {
	const { keepName, keepIsStandard, keepProps, keepType } = keepParams;

	const details = keepProps ? props.propDetails ?? null : null;

	if (!keepName) name.value = props.propName ?? "";
	if (!keepIsStandard) isStandard.value = details?.isStandard ? "true" : "false";

	value.value = details?.value ?? "";

	if (details?.isStandard) {
		const nextType = keepType ? standardPropOptions.type : details?.standardOptions?.type ?? "string";

		Object.assign(standardPropOptions, {
			...details?.standardOptions,
			isRequired: Boolean(details?.standardOptions?.isRequired),
			type: nextType,
		});

		const deps = details?.standardOptions?.dependencies ?? {};
		Object.keys(standardPropDependencyMap).forEach((k) => delete standardPropDependencyMap[k]);
		Object.assign(standardPropDependencyMap, deps);
	} else if (isStandardBool.value) {
		if (!keepType) {
			standardPropOptions.type = "string";
		}

		Object.assign(standardPropOptions, {
			isRequired: false,
			type: standardPropOptions.type,
			// defaultValue: "",
			options: {},
			dependencies: {},
		});

		Object.assign(standardPropDependencyMap, {});
	} else {
		if (!keepType) {
			selectedNonStandardPropType.value = details?.isDynamic ? "dynamic" : "static";
		}
	}

	optionsComponentRef.value?.reset(!!keepProps);
};

watch(
	[() => props.propName, () => props.propDetails],
	() =>
		reset({
			keepName: false,
			keepIsStandard: false,
			keepProps: true,
			keepType: false,
		}),
	{
		immediate: true,
		deep: true,
	},
);

watch(
	selectedPropType,
	() => {
		autoCompleteRef.value?.refreshOptions();
	},
	{ immediate: true },
);

const save = async () => {
	await nextTick();
	const propValue: BlockProps[string] = {
		isStandard: isStandardBool.value,
		isDynamic: isStandardBool.value ? false : selectedNonStandardPropType.value === "dynamic", // all standard props are static by default
		comesFrom: comesFrom.value,
		value: isStandardBool.value ? null : value.value,
		standardOptions: isStandardBool.value
			? {
					...standardPropOptions,
					dependencies: standardPropDependencyMap.value,
			  }
			: undefined,
	};
	if (props.mode === "add") {
		emit("add:prop", { name: name.value, value: propValue });
	} else {
		emit("update:prop", { oldPropName: props.propName!, newName: name.value, newValue: propValue });
	}
};
defineExpose({ reset });
</script>
