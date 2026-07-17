import SpacingControl from "@/components/SpacingControl.vue";
import blockController from "@/utils/blockController";

const spacingSectionProperties = [
	{
		component: SpacingControl,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => ({ type: "margin" }),
		condition: () => !blockController.isRoot(),
	},
	{
		component: SpacingControl,
		searchKeyWords: "Padding, Top, PaddingTop, Padding Top",
		getProps: () => ({ type: "padding" }),
	},
];

export default {
	name: "Spacing",
	properties: spacingSectionProperties,
};
