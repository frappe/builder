import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const dataKeySectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "键",
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
				label: "类型",
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
				label: "属性",
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
	name: "数据键",
	properties: dataKeySectionProperties,
	collapsed: computed(() => {
		return !blockController.getDataKey("key") && !blockController.isRepeater();
	}),
};
