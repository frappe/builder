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
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { getDataArray, getDefaultPropsList, getParentProps, getRepeaterScopedData } from "@/utils/helpers";
import { computed, ref, watch } from "vue";

const props = defineProps<{
	label: string;
	getModelValue: () => string;
	setModelValue: (value: BlockVisibilityCondition) => void;
}>();

const pageStore = usePageStore();
const componentStore = useComponentStore();
const { editingMode, fragmentData } = useCanvasStore();

const currentBlock = computed(() => blockController.getFirstSelectedBlock());
const autocompleteRef = ref<InstanceType<typeof InlineInput> | null>(null);

const pageDataArray = computed(() => {
	if (!currentBlock.value) {
		return [];
	}
	return getDataArray(getRepeaterScopedData(currentBlock.value, pageStore.pageData));
});

let componentData = {};
if (editingMode == "fragment") {
	const componentId = fragmentData.fragmentId;
	const blockId = fragmentData.block?.blockId;
	componentData = componentStore.getComponentInstanceData(componentId!, blockId);
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
	return Object.keys(getDefaultPropsList(currentBlock.value, blockController));
});
const getOptions = async (query: string) => {
	let options: { label: string; value: string }[] = [];

	pageDataArray.value.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--dataScript`,
			});
		}
	});
	componentDataArray.value.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--componentData`,
			});
		}
	});
	const combinedProps = [...new Set([...ownProps.value, ...parentProps.value])];

	combinedProps.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--props`,
			});
		}
	});
	defaultProps.value.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--props`,
			});
		}
	});

	return options;
};

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
