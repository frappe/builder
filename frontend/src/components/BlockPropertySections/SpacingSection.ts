import blockController from "@/utils/blockController";
import { computed } from "vue";
import PropertyControl from "../Controls/PropertyControl.vue";

const spacingSectionProperties = [
	{
		component: PropertyControl,
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
		component: PropertyControl,
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
