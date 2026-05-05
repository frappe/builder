import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";

const spacingSectionProperties = [
	{
		component: StylePropertyControl,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => {
			return {
				label: "Margin",
				getModelValue: () => blockController.getMargin({ nativeOnly: true }),
				getPlaceholder: () => blockController.getMargin({ cascading: true }),
				setModelValue: (val: string) => blockController.setMargin(val),
				propertyKey: "margin",
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
		component: StylePropertyControl,
		searchKeyWords: "Padding, Top, PaddingTop, Padding Top",
		getProps: () => {
			return {
				label: "Padding",
				enableSlider: true,
				unitOptions: ["px", "em", "rem"],
				getModelValue: () => blockController.getPadding({ nativeOnly: true }),
				getPlaceholder: () => blockController.getPadding({ cascading: true }),
				setModelValue: (val: string) => blockController.setPadding(val),
				propertyKey: "padding",
			};
		},
	},
];

export default {
	name: "Spacing",
	properties: spacingSectionProperties,
};
