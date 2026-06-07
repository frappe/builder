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
import { useBlockDataStore } from "@/stores/blockStore";
import blockController from "@/utils/blockController";
import { getDataArray, getDefaultPropsList, getParentProps } from "@/utils/helpers";
import { computed, ref, watch } from "vue";

const props = defineProps<{
	label: string;
	getModelValue: () => string;
	setModelValue: (value: BlockVisibilityCondition) => void;
}>();

const blockDataStore = useBlockDataStore();

const autocompleteRef = ref<InstanceType<typeof InlineInput> | null>(null);

const pageDataArray = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (!currentBlock) {
		return [];
	}
	return getDataArray(blockDataStore.getPageData(currentBlock.blockId) || {});
});
const blockDataArray = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (!currentBlock) {
		return [];
	}
	return getDataArray(blockDataStore.getBlockData(currentBlock.blockId) || {});
});
const ownProps = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (!currentBlock) {
		return [];
	}
	return Object.keys(currentBlock.getBlockProps());
});
const parentProps = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (!currentBlock) {
		return [];
	}
	return Object.keys(getParentProps(currentBlock));
});
const defaultProps = computed(() => {
	const currentBlock = blockController.getFirstSelectedBlock();
	if (!currentBlock) {
		return [];
	}
	return Object.keys(getDefaultPropsList(currentBlock, blockController));
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
	blockDataArray.value.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--blockDataScript`,
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
	[pageDataArray, blockDataArray, ownProps, parentProps, defaultProps],
	() => {
		autocompleteRef.value?.refreshOptions();
	},
	{ immediate: true },
);
</script>
