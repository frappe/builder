import Autocomplete from "@/components/Controls/Autocomplete.vue";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { getCollectionKeys, getDataForKey } from "@/utils/helpers";
import { FeatherIcon } from "frappe-ui";
import { computed, h } from "vue";

const keyOptions = computed(() => {
	const pageStore = usePageStore();
	let result: { label: string; value: string; prefix: any }[] = [];
	const repeatableDataKeys: string[] = [];
	let collectionObject = pageStore.pageData;

	if (blockController.getFirstSelectedBlock()?.isInsideRepeater()) {
		const keys = getCollectionKeys(blockController.getFirstSelectedBlock());
		collectionObject = keys.reduce((acc: any, key: string) => {
			const data = getDataForKey(acc, key);
			return Array.isArray(data) && data.length > 0 ? data[0] : data;
		}, collectionObject);
	}

	function processObject(obj: Record<string, any>, prefix = "") {
		if (!obj || typeof obj !== "object") {
			return;
		}

		Object.entries(obj).forEach(([key, value]) => {
			const path = prefix ? `${prefix}.${key}` : key;

			if (Array.isArray(value)) {
				repeatableDataKeys.push(path);
			} else if (typeof value === "object" && value !== null) {
				processObject(value, path);
			}
		});
	}

	processObject(collectionObject);

	const repeatableProps: string[] = [];
	
	const isInsideRepeater = blockController.getFirstSelectedBlock()?.isInsideRepeater();
	const isPropsBasedRepeater =
		isInsideRepeater &&
		blockController.getFirstSelectedBlock()?.getRepeaterParent()?.getDataKey("comesFrom") === "props";
	const propsOfComponentRoot = blockController.getComponentRootBlock()?.getBlockProps();
	
	if (propsOfComponentRoot && !isPropsBasedRepeater) {
		Object.entries(propsOfComponentRoot).forEach(([key, value]) => {
			if (
				value.isStandard &&
				(value.standardOptions?.type == "array" || value.standardOptions?.type == "object")
			) {
				repeatableProps.push(key);
			}
		});
	}

	repeatableDataKeys.forEach((item) => {
		result.push({
			label: item,
			value: `${item}--pgdata`,
			prefix: h(FeatherIcon, {
				name: "zap",
				class: "size-3",
			}),
		});
	});
	repeatableProps.forEach((prop) => {
		result.push({
			label: prop,
			value: `${prop}--stprop`,
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
				let value = selectedOption.slice(0, -8);
				let comesFromShort = selectedOption.slice(-6);
				let comesFrom: BlockDataKey["comesFrom"] | "" = "dataScript";
				if (!value && useCanvasStore().editingMode != "fragment") {
					comesFrom = "";
				}
				if (comesFromShort == "stprop") {
					comesFrom = "props";
				}
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
