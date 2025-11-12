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
				@update:model-value="(val) => (isStandard = val)" />
		</div>
		<div class="flex items-center justify-between">
			<InputLabel>Name</InputLabel>
			<Input v-model="name" placeholder="Enter prop name"></Input>
		</div>
		<div class="flex items-center justify-between">
			<InputLabel>Type</InputLabel>
			<Input
				placeholder="Select prop type"
				type="select"
				:options="propTypes"
				:model-value="selectedPropType"
				@update:model-value="
					(option) => {
						setPropType(option);
					}
				"></Input>
		</div>
		<div v-if="!isStandardBool" class="flex items-center justify-between">
			<InputLabel v-model="value">Value</InputLabel>
			<Input v-if="selectedPropType == 'static'" v-model="value" placeholder="Enter prop name"></Input>
			<Autocomplete
				v-else
				:is-teleported="true"
				teleported-to=".props-popover-content"
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
					:model-value="standardPropOptions.isRequired"
					@update:model-value="(val) => (standardPropOptions.isRequired = val)" />
			</div>
			<component :is="componentMapping[selectedStandardPropType as keyof typeof componentMapping]" />
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
		<hr />
		<div class="flex items-center justify-between">
			<BuilderButton class="w-full">Save</BuilderButton>
		</div>
	</div>
</template>

<script setup lang="ts">
import InputLabel from "@/components/Controls/InputLabel.vue";
import Input from "@/components/Controls/Input.vue";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import NumberOptions from "@/components/PropsOptions/NumberOptions.vue";
import StringOptions from "@/components/PropsOptions/StringOptions.vue";
import ArrayOptions from "@/components/PropsOptions/ArrayOptions.vue";
import PropsDependencyEditor from "@/components/PropsDependencyEditor.vue";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import ObjectOptions from "@/components/PropsOptions/ObjectOptions.vue";
import BooleanOptions from "@/components/PropsOptions/BooleanOptions.vue";
import BuilderButton from "./Controls/BuilderButton.vue";
import Autocomplete from "./Controls/Autocomplete.vue";
import usePageStore from "@/stores/pageStore";
import { getCollectionKeys, getDataForKey } from "@/utils/helpers";
import Block from "@/block";

const canvasStore = useCanvasStore();

const isStandard = ref("false");
const isStandardBool = computed(() => isStandard.value === "true");
const isEditable = ref("false");
const name = ref("");
const value = ref("");
const selectedNonStandardPropType = ref("static");
const selectedStandardPropType = ref("string");
const standardPropOptions = ref<{ isRequired: string; [key: string]: any }>({
	isRequired: "false",
});
const standardPropDependencyMap = ref<{ [key: string]: any }>({});
const autoCompleteRef = ref<typeof Autocomplete | null>(null);

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
		return selectedStandardPropType.value;
	} else {
		return selectedNonStandardPropType.value;
	}
});

const setPropType = (type: string) => {
	if (isStandardBool.value) {
		selectedStandardPropType.value = type;
	} else {
		selectedNonStandardPropType.value = type;
	}
};

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

watch(
	selectedPropType,
	() => {
		if (Array.isArray(autoCompleteRef.value)) {
			autoCompleteRef.value.forEach((ref) => {
				ref?.updateOptions();
			});
		}
	},
	{ immediate: true },
);
</script>
