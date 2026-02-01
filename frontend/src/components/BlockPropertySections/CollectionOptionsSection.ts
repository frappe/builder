import Autocomplete from "@/components/Controls/Autocomplete.vue";
import useBlockDataStore from "@/stores/blockDataStore";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import { FeatherIcon } from "frappe-ui";
import { computed, h } from "vue";

const keyOptions = computed(() => {
	const blockDataStore = useBlockDataStore();
	let result: { label: string; value: string; prefix: any }[] = [];

	const repeatablePageDataKeys: string[] = [];
	const repeatableBlockDataKeys: string[] = [];

	let pageDataCollectionObject =
		blockDataStore.getPageData(blockController.getFirstSelectedBlock()?.blockId || "") || {};
	let blockDataCollectionObject =
		blockDataStore.getBlockData(blockController.getFirstSelectedBlock()?.blockId || "") || {};

	const isInsideRepeater = blockController.getFirstSelectedBlock()?.isInsideRepeater();
	const repeaterDataKeyComesFrom: BlockDataKey["comesFrom"] | undefined = blockController
		.getFirstSelectedBlock()
		?.getRepeaterParent()
		?.getDataKey("comesFrom") as BlockDataKey["comesFrom"] | undefined;


	function processObject(obj: Record<string, any>, prefix = "", resultArray: string[] = []) {
		if (!obj || typeof obj !== "object") {
			return;
		}

		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (Array.isArray(value)) {
				resultArray.push(path);
			} else if (typeof value === "object" && value !== null) {
				processObject(value, path, resultArray);
			}
		});
	}

	processObject(pageDataCollectionObject, "", repeatablePageDataKeys);
	processObject(blockDataCollectionObject, "", repeatableBlockDataKeys);

	const isPropsBasedRepeater = isInsideRepeater && repeaterDataKeyComesFrom == "props";
	const repeatableProps: string[] = [];

	const propsOfComponentRoot = blockController.getComponentRootBlock()?.getBlockProps();

	if (propsOfComponentRoot && !isPropsBasedRepeater) {
		Object.entries(propsOfComponentRoot).forEach(([key, value]) => {
			if (
				value.isStandard &&
				(value.propOptions?.type == "array" || value.propOptions?.type == "object")
			) {
				repeatableProps.push(key);
			}
		});
	}

	repeatablePageDataKeys.forEach((item) => {
		result.push({
			label: item,
			value: `${item}--dataScript`,
			prefix: h(FeatherIcon, {
				name: "zap",
				class: "size-3",
			}),
		});
	});
	repeatableBlockDataKeys.forEach((item) => {
		result.push({
			label: item,
			value: `${item}--blockDataScript`,
			prefix: h(FeatherIcon, {
				name: "zap",
				class: "size-3",
			}),
		});
	});
	repeatableProps.forEach((prop) => {
		result.push({
			label: prop,
			value: `${prop}--props`,
			prefix: h(FeatherIcon, {
				name: "git-commit",
				class: "size-3",
			}),
		});
	});

	return result;
});

const collectionOptions = [
	{
		component: Autocomplete,
		getProps: () => {
			return {
				label: "Key",
				modelValue: blockController.getDataKey("key"),
				placeholder: "Select a collection",
				options: keyOptions.value,
			};
		},
		searchKeyWords: "Collection, Repeater, Dynamic Collection, Dynamic Repeater",
		events: {
			"update:modelValue": (selectedOption: string) => {
				let value = selectedOption.split("--").slice(0, -1).join("--");
				let comesFrom = selectedOption.split("--").slice(-1)[0] as BlockDataKey["comesFrom"];
				blockController.setDataKey("key", value);
				blockController.setDataKey("comesFrom", comesFrom);
			},
		},
	},
];

export default {
	name: "Collection",
	properties: collectionOptions,
	condition: () => blockController.isRepeater(),
};
