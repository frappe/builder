import blockController from "@/utils/blockController";
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
				enableSlider: true,
				unitOptions: ["px", "em", "rem"],
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
				enableSlider: true,
				unitOptions: ["px", "em", "rem"],
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
};
