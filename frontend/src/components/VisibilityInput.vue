<template>
	<GenericControl
		:component="Autocomplete"
		:label="label"
		:getOptions="getOptions"
		:getModelValue="getModelValue"
		@update:modelValue="handleModelValueUpdate" />
</template>
<script setup lang="ts">
import Autocomplete from "@/components/Controls/Autocomplete.vue";
import GenericControl from "@/components/Controls/GenericControl.vue";
import useBlockDataStore from "@/stores/blockDataStore";
import blockController from "@/utils/blockController";
import { getDataArray, getParentProps, getStandardPropValue } from "@/utils/helpers";

const props = defineProps<{
	property: styleProperty;
	label: string;
	getModelValue: () => string;
	setModelValue: (value: BlockVisibilityCondition) => void;
}>();

const getOptions = async (query: string) => {
	const blockDataStore = useBlockDataStore();

	let options: { label: string; value: string }[] = [];

	let pageDataArray: string[] = [];
	let blockDataArray: string[] = [];
	let ownProps: string[] = [];
	let parentProps: string[] = [];
	let defaultProps: string[] = [];

	const currentBlock = blockController.getFirstSelectedBlock();

	if (!currentBlock) {
		return options;
	}

	if (currentBlock) {

		pageDataArray = getDataArray(
			currentBlock,
			blockDataStore.getPageData(currentBlock.blockId) || {},
			"dataScript",
		);

		blockDataArray = getDataArray(
			currentBlock,
			blockDataStore.getBlockData(currentBlock.blockId) || {},
			"blockDataScript",
		);

		ownProps = Object.keys(currentBlock.getBlockProps());

		parentProps = Object.keys(getParentProps(currentBlock, {}));

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
					defaultProps = ["item"];
				} else if (typeof parsedValue === "object") {
					defaultProps = ["key", "value"];
				}
			}
		}
	}

	const combinedProps = [...ownProps, ...parentProps].reduce((acc, prop) => {
		if (!acc.find((p: string) => p === prop)) {
			acc.push(prop);
		}
		return acc;
	}, [] as string[]);

	console.log({ pageDataArray, blockDataArray, combinedProps }, query);

	pageDataArray.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--dataScript`,
			});
		}
	});
	blockDataArray.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--blockDataScript`,
			});
		}
	});

	combinedProps.map((prop) => {
		if (query.trim() == "" || prop.toLowerCase().includes(query.toLowerCase())) {
			options.push({
				label: prop,
				value: `${prop}--props`,
			});
		}
	});
	defaultProps.map((prop) => {
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
</script>
