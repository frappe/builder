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
				:modelValue="value"
				:getOptions="getOptions"
				@update:modelValue="
					(option) => {
						if (typeof option === 'string') {
							return;
						} else {
							value = option?.value;
						}
					}
				" />
		</div>
		<div v-if="!isStandardBool && isInFragmentMode" class="flex items-center justify-between">
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
				:options="standardPropOptions"
				@update:options="(option: any) => {
					console.log('option', option);
					standardPropOptions = {
						isRequired: standardPropOptions.isRequired,
						type: standardPropOptions.type,
						dependencies: standardPropOptions.dependencies,
						...option,
					};
				}" />
		</template>
		<div v-if="isStandardBool" class="flex flex-col gap-2">
			<InputLabel>Depends on</InputLabel>
			<PropsDependencyEditor
				:available-std-props="{
					sample_prop: 'string',
					another_prop: 'number',
					one_more_prop: 'boolean',
					list_prop: 'array',
					obj_prop: 'object',
				}"
				:obj="standardPropDependencyMap"
				@update:obj="(obj) => (standardPropDependencyMap = obj)" />
		</div>
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

import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

import PropsDependencyEditor from "@/components/PropsDependencyEditor.vue";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";

import NumberOptions from "@/components/PropsOptions/NumberOptions.vue";
import StringOptions from "@/components/PropsOptions/StringOptions.vue";
import ArrayOptions from "@/components/PropsOptions/ArrayOptions.vue";
import ObjectOptions from "@/components/PropsOptions/ObjectOptions.vue";
import BooleanOptions from "@/components/PropsOptions/BooleanOptions.vue";

import usePageStore from "@/stores/pageStore";
import { getCollectionKeys, getDataForKey } from "@/utils/helpers";

const props = withDefaults(
	defineProps<{
		mode: "add" | "edit";
		propName?: string | null;
		propDetails?: BlockProps[string] | null;
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
const selectedNonStandardPropType = ref(
	props.propDetails && !props.propDetails.isStandard ? props.propDetails.type : "static",
);
const standardPropOptions = ref<BlockPropsStandardOptions>(
	props.propDetails && props.propDetails.isStandard
		? {
				...props.propDetails.standardOptions,
				isRequired: Boolean(props.propDetails.standardOptions?.isRequired),
				type: props.propDetails.standardOptions?.type || "string",
		  }
		: {
				isRequired: false,
				type: "string",
				defaultValue: "",
				options: [],
				dependencies: {},
		  },
);
const standardPropDependencyMap = ref<{ [key: string]: any }>(
	props.propDetails && props.propDetails.isStandard
		? props.propDetails.standardOptions?.dependencies || {}
		: {},
);
const autoCompleteRef = ref<typeof Autocomplete | null>(null);

const emit = defineEmits({
	"add:prop": (name: string, prop: BlockProps[string]) => true,
	"update:prop": (oldPropName: string, newName: string, newProp: BlockProps[string]) => true,
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
				label: "Inherited",
				value: "inherited",
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
		console.log("standardPropOptions.value.type", standardPropOptions.value.type);
		return standardPropOptions.value.type;
	} else {
		return selectedNonStandardPropType.value;
	}
});

const STANDARD_PROP_TYPES = ["string", "number", "boolean", "array", "object"];

const setPropType = (type: string) => {
	if (isStandardBool.value && STANDARD_PROP_TYPES.includes(type)) {
		standardPropOptions.value.type = type as "string" | "number" | "boolean" | "array" | "object";
	} else {
		selectedNonStandardPropType.value = type as "static" | "inherited" | "dynamic";
	}
};

// TODO: reuse this from dynamic value handler
const dataArray = computed(() => {
	const result: string[] = [];
	let collectionObject = usePageStore().pageData;
	if (blockController.getFirstSelectedBlock()?.isInsideRepeater()) {
		const keys = getCollectionKeys(blockController.getFirstSelectedBlock());
		collectionObject = keys.reduce((acc: any, key: string) => {
			const data = getDataForKey(acc, key);
			return Array.isArray(data) && data.length > 0 ? data[0] : data;
		}, collectionObject);
	}

	function processObject(obj: Record<string, any>, prefix = "") {
		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (typeof value === "object" && value !== null && !Array.isArray(value)) {
				processObject(value, path);
			} else if (["string", "number", "boolean"].includes(typeof value)) {
				result.push(path);
			}
		});
	}

	processObject(collectionObject);
	return result;
});

const getParentProps = (baseBlock: Block, baseProps: string[]): string[] => {
	const parentBlock = baseBlock.getParentBlock();
	if (parentBlock) {
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
	let options: string[];
	if (selectedPropType.value == "inherited") {
		options = getParentProps(blockController.getFirstSelectedBlock()!, []);
	} else {
		options = dataArray.value;
	}

	return options
		.filter((prop) => prop.toLowerCase().includes(query.toLowerCase()))
		.map((prop) => ({
			label: prop,
			value: prop,
		}));
};

const componentMapping = {
	string: StringOptions,
	number: NumberOptions,
	array: ArrayOptions,
	boolean: BooleanOptions,
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

const reset = async (keepParams: {
	keepName: boolean;
	keepIsStandard: boolean;
	keepProps: boolean;
	keepType: boolean;
}) => {
	const { keepName, keepIsStandard, keepProps, keepType } = keepParams;
	if (!keepName) name.value = props.propName ?? "";
	const propDetails = keepProps ? props.propDetails : null;
	if (!keepIsStandard) isStandard.value = propDetails?.isStandard ? "true" : "false";
	value.value = propDetails?.value ?? "";
	console.trace("val", keepParams, propDetails?.value ?? "hello");
	if (propDetails?.isStandard) {
		standardPropOptions.value = {
			...propDetails.standardOptions,
			isRequired: Boolean(propDetails.standardOptions?.isRequired),
			...(keepType
				? { type: standardPropOptions.value.type }
				: { type: propDetails.standardOptions?.type || "string" }),
		};
		standardPropDependencyMap.value = propDetails.standardOptions?.dependencies || {};
	} else {
		if (!keepType) selectedNonStandardPropType.value = propDetails?.type || "static";
	}
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
		autoCompleteRef.value?.updateOptions();
	},
	{ immediate: true },
);

const save = async () => {
	await nextTick();
	const propValue: BlockProps[string] = {
		isStandard: isStandardBool.value,
		type: isStandardBool.value ? "static" : selectedNonStandardPropType.value,
		value: isStandardBool.value ? null : value.value,
		standardOptions: isStandardBool.value
			? {
					...standardPropOptions.value,
					dependencies: standardPropDependencyMap.value,
			  }
			: undefined,
	};
	if (props.mode === "add") {
		emit("add:prop", name.value, propValue);
	} else {
		emit("update:prop", props.propName!, name.value, propValue);
	}
};

defineExpose({ reset });
</script>
