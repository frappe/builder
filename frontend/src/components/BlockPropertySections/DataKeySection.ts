import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const dataKeySectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Key",
				modelValue: blockController.getDataKey("key"),
			};
		},
		searchKeyWords: "Key, DataKey, Data Key",
		events: {
			"update:modelValue": (val: string) => blockController.setDataKey("key", val),
		},
	},
	{
		component: InlineInput,
		condition: () => !blockController.isRepeater(),
		getProps: () => {
			return {
				label: "Type",
				modelValue: blockController.getDataKey("type"),
			};
		},
		searchKeyWords: "Type, DataType, Data Type",
		events: {
			"update:modelValue": (val: string) => blockController.setDataKey("type", val),
		},
	},
	{
		component: InlineInput,
		condition: () => !blockController.isRepeater(),
		getProps: () => {
			return {
				label: "Property",
				modelValue: blockController.getDataKey("property"),
			};
		},
		searchKeyWords: "Property, DataProperty, Data Property",
		events: {
			"update:modelValue": (val: string) => blockController.setDataKey("property", val),
		},
	},
];

export default {
	name: "Data Key",
	properties: dataKeySectionProperties,
	collapsed: computed(() => {
		return !blockController.getDataKey("key") && !blockController.isRepeater();
	}),
};
