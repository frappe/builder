import BackgroundHandler from "@/components/BackgroundHandler.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import blockController from "@/utils/blockController";
import InlineInputWithStates from "../Controls/InlineInputWithStates.vue";
import StyleControl from "../Controls/StyleControl.vue";

const styleSectionProperties = [
	{
		component: BackgroundHandler,
		getProps: () => {},
		searchKeyWords:
			"Background, BackgroundImage, Background Image, Background Position, Background Repeat, Background Size, BG, BGImage, BG Image, BGPosition, BG Position, BGRepeat, BG Repeat, BGSize, BG Size",
	},
	{
		component: ColorInput,
		getProps: () => {
			return {
				label: "Text Color",
				value: blockController.getTextColor(),
			};
		},
		searchKeyWords: "Text, Color, TextColor, Text Color",
		events: {
			change: (val: string) => blockController.setTextColor(val),
		},
	},
	{
		component: ColorInput,
		getProps: () => {
			return {
				label: "Border Color",
				value: blockController.getStyle("borderColor"),
			};
		},
		searchKeyWords: "Border, Color, BorderColor, Border Color",
		events: {
			change: (val: StyleValue) => {
				blockController.setStyle("borderColor", val);
				if (val) {
					if (!blockController.getStyle("borderWidth")) {
						blockController.setStyle("borderWidth", "1px");
						blockController.setStyle("borderStyle", "solid");
					}
				} else {
					blockController.setStyle("borderWidth", null);
					blockController.setStyle("borderStyle", null);
				}
			},
		},
	},
	{
		component: StyleControl,
		getProps: () => {
			return {
				label: "Border Width",
				styleProperty: "borderWidth",
				enableSlider: true,
				unitOptions: ["px", "%", "em", "rem"],
				minValue: 0,
			};
		},
		searchKeyWords: "Border, Width, BorderWidth, Border Width",
		condition: () => blockController.getStyle("borderColor") || blockController.getStyle("borderWidth"),
	},
	{
		component: StyleControl,
		getProps: () => {
			return {
				label: "Border Style",
				styleProperty: "borderStyle",
				type: "select",
				options: [
					{ value: "solid", label: "Solid" },
					{ value: "dashed", label: "Dashed" },
					{ value: "dotted", label: "Dotted" },
				],
			};
		},
		searchKeyWords: "Border, Style, BorderStyle, Border Style, Solid, Dashed, Dotted",
		condition: () => blockController.getStyle("borderColor"),
	},
	{
		component: StyleControl,
		getProps: () => {
			return {
				label: "Shadow",
				styleProperty: "boxShadow",
				type: "select",
				options: [
					{ value: null, label: "None" },
					{
						label: "Small",
						value: "rgba(0, 0, 0, 0.05) 0px 1px 2px 0px, rgba(0, 0, 0, 0.05) 0px 1px 3px 0px",
					},
					{
						label: "Medium",
						value: "rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.1) 0px 4px 6px -4px",
					},
					{
						label: "Large",
						value: "rgba(0, 0, 0, 0.1) 0px 20px 25px -5px, rgba(0, 0, 0, 0.1) 0px 10px 10px -5px",
					},
				],
			};
		},
		searchKeyWords: "Shadow, BoxShadow, Box Shadow",
	},
	{
		component: InlineInputWithStates,
		getProps: () => {
			return {
				label: "Radius",
				modelValue: blockController.getStyle("borderRadius"),
				hoverStyle: blockController.getStyle("hover:borderRadius"),
				enableSlider: true,
				unitOptions: ["px", "%"],
				minValue: 0,
			};
		},
		searchKeyWords: "Border, Radius, BorderRadius, Border Radius",
		events: {
			"update:modelValue": (val: StyleValue) => {
				blockController.setStyle("borderRadius", val);
				if (val) {
					if (!blockController.getStyle("overflowX")) {
						blockController.setStyle("overflowX", "hidden");
					}
					if (!blockController.getStyle("overflowY")) {
						blockController.setStyle("overflowY", "hidden");
					}
				}
			},
			setHoverStyle: (val: StyleValue) => {
				blockController.setStyle("hover:borderRadius", val);
			},
		},
	},
	{
		component: StyleControl,
		getProps: () => {
			return {
				label: "Z-Index",
				styleProperty: "zIndex",
			};
		},
		searchKeyWords: "Z, Index, ZIndex, Z Index",
		condition: () =>
			!blockController.multipleBlocksSelected() &&
			!blockController.isRoot() &&
			blockController.getStyle("position") !== "static",
	},
];

export default {
	name: "Style",
	properties: styleSectionProperties,
};
