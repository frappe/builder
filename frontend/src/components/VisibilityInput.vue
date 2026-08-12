<template>
	<InlineInput
		:label="label"
		type="autocomplete"
		ref="autocompleteRef"
		:modelValue="getModelValue()"
		:getOptions="getOptions"
		@update:modelValue="handleModelValueUpdate" />
</template>
<script setup lang="ts">
import InlineInput from "@/components/Controls/InlineInput.vue";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { filterOptions } from "@/utils/autocompleteOptions";
import blockController from "@/utils/blockController";
import componentController from "@/utils/componentController";
import { getDataArray, getDefaultPropsList, getParentProps, getRepeaterScopedData } from "@/utils/helpers";
import { computed, ref, watch } from "vue";

const props = defineProps<{
	label: string;
	getModelValue: () => string;
	setModelValue: (value: BlockVisibilityCondition) => void;
}>();

const pageStore = usePageStore();
const canvasStore = useCanvasStore();

const currentBlock = computed(() => blockController.getFirstSelectedBlock());
const autocompleteRef = ref<InstanceType<typeof InlineInput> | null>(null);

const pageDataArray = computed(() => {
	if (!currentBlock.value) {
		return [];
	}
	return getDataArray(getRepeaterScopedData(currentBlock.value, pageStore.pageData));
});

let componentData = {};
if (canvasStore.editingMode == "fragment") {
	componentData = componentController.getComponentDataPreview();
}

const componentDataArray = computed(() => {
	if (!currentBlock.value) {
		return [];
	}
	return getDataArray(getRepeaterScopedData(currentBlock.value, componentData));
});

const ownProps = computed(() => {
	if (!currentBlock.value) {
		return [];
	}
	return Object.keys(currentBlock.value.getBlockProps());
});
const parentProps = computed(() => {
	if (!currentBlock.value) {
		return [];
	}
	return Object.keys(getParentProps(currentBlock.value));
});

const defaultProps = computed(() => {
	if (!currentBlock.value) {
		return [];
	}
	return Object.keys(getDefaultPropsList(currentBlock.value));
});
const visibilityOptions = computed(() => {
	const toOptions = (props: string[], comesFrom: string) =>
		props.map((prop) => ({ label: prop, value: `${prop}--${comesFrom}` }));
	const propsList = [...new Set([...ownProps.value, ...parentProps.value, ...defaultProps.value])];

	return [
		...toOptions(pageDataArray.value, "dataScript"),
		...toOptions(componentDataArray.value, "componentData"),
		...toOptions(propsList, "props"),
	];
});

const getOptions = async (query: string) => filterOptions(visibilityOptions.value, query);

const handleModelValueUpdate = (value: string | null) => {
	if (value == null) {
		props.setModelValue({ key: undefined, comesFrom: undefined });
		return;
	}
	const key = value.split("--").slice(0, -1).join("--");
	const comesFrom = value.split("--").slice(-1)[0];
	props.setModelValue({ key, comesFrom: comesFrom as BlockVisibilityCondition["comesFrom"] });
};

watch(
	[pageDataArray, ownProps, parentProps, defaultProps],
	() => {
		autocompleteRef.value?.refreshOptions();
	},
	{ immediate: true },
);
</script>
