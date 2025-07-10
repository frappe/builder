import Autocomplete from "@/components/Controls/Autocomplete.vue";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";

const collectionOptions = [
	{
		component: Autocomplete,
		getProps: () => {
			return {
				label: "Key",
				modelValue: blockController.getDataKey("key"),
				placeholder: "Select a collection",
				getOptions() {
					const pageStore = usePageStore();
					const keys = Object.keys(pageStore.pageData).filter((key) =>
						Array.isArray(pageStore.pageData[key]),
					);
					return keys.map((key) => ({
						label: key,
						value: key,
					}));
				},
			};
		},
		searchKeyWords: "Collection, Repeater, Dynamic Collection, Dynamic Repeater",
		events: {
			"update:modelValue": (selectedOption: { label: string; value: string }) => {
				blockController.setDataKey("key", selectedOption.value);
			},
		},
	},
];

export default {
	name: "Collection",
	properties: collectionOptions,
	condition: () => blockController.isRepeater(),
};
