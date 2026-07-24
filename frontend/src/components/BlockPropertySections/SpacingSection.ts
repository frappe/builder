import SpacingControl from "@/components/SpacingControl.vue";
import blockController from "@/utils/blockController";

const spacingSectionProperties = [
	{
		component: SpacingControl,
		searchKeyWords: "Margin, Top, MarginTop, Margin Top",
		getProps: () => ({ type: "margin" }),
		ownedStyleProperties: ["margin", "margin-bottom", "margin-left", "margin-right", "margin-top"],
		condition: () => !blockController.isRoot(),
	},
	{
		component: SpacingControl,
		searchKeyWords: "Padding, Top, PaddingTop, Padding Top",
		getProps: () => ({ type: "padding" }),
		ownedStyleProperties: ["padding", "padding-bottom", "padding-left", "padding-right", "padding-top"],
	},
];

export default {
	name: "Spacing",
	properties: spacingSectionProperties,
};
