import Autocomplete from "@/components/Controls/Autocomplete.vue";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { getCollectionKeys, getDataForKey } from "@/utils/helpers";
import { computed } from "vue";

const keyOptions = computed(() => {
	const pageStore = usePageStore();
	const result: string[] = [];
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
				result.push(path);
			} else if (typeof value === "object" && value !== null) {
				processObject(value, path);
			}
		});
	}

	processObject(collectionObject);
	return result.map((key) => ({
		label: key,
		value: key,
	}));
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
			"update:modelValue": (selectedOption: { label: string; value: string }) => {
				blockController.setDataKey("key", selectedOption?.value);
			},
		},
	},
];

export default {
	name: "Collection",
	properties: collectionOptions,
	condition: () => blockController.isRepeater(),
};
