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

					function getNestedArrayKeys(obj: any, prefix = ""): string[] {
						const keys: string[] = [];

						for (const [key, value] of Object.entries(obj)) {
							const fullKey = prefix ? `${prefix}.${key}` : key;

							if (Array.isArray(value)) {
								keys.push(fullKey);
							} else if (value && typeof value === "object") {
								keys.push(...getNestedArrayKeys(value, fullKey));
							}
						}

						return keys;
					}

					const keys = getNestedArrayKeys(pageStore.pageData);
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
