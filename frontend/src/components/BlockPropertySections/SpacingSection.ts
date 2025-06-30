import blockController from "@/utils/blockController";
import { computed } from "vue";
import StyleControl from "../Controls/StyleControl.vue";

const spacingSectionProperties = [
	{
		component: StyleControl,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => {
			return {
				label: "Margin",
				getModelValue: () => blockController.getMargin({ nativeOnly: true }),
				getPlaceholder: () => blockController.getMargin({ cascading: true }),
				setModelValue: (val: string) => blockController.setMargin(val),
				styleProperty: "margin",
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setMargin(val),
		},
		condition: () => !blockController.isRoot(),
	},
	{
		component: StyleControl,
		searchKeyWords: "Padding, Top, PaddingTop, Padding Top",
		getProps: () => {
			return {
				label: "Padding",
				getModelValue: () => blockController.getPadding({ nativeOnly: true }),
				getPlaceholder: () => blockController.getPadding({ cascading: true }),
				setModelValue: (val: string) => blockController.setPadding(val),
				styleProperty: "padding",
			};
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
