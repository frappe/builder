import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const spacingSectionProperties = [
	{
		component: InlineInput,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => {
			return {
				label: "Margin",
				modelValue: blockController.getMargin(),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setMargin(val),
		},
		condition: () => !blockController.isRoot(),
	},
	{
		component: InlineInput,
		searchKeyWords: "Padding, Top, PaddingTop, Padding Top",
		getProps: () => {
			return {
				label: "Padding",
				modelValue: blockController.getPadding(),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setPadding(val),
		},
	},
];

export default {
	name: "Spacing",
	properties: spacingSectionProperties,
	collapsed: computed(
		() =>
			!blockController.getStyle("marginTop") &&
			!blockController.getStyle("paddingTop") &&
			!blockController.getStyle("marginBottom") &&
			!blockController.getStyle("paddingBottom"),
	),
};
