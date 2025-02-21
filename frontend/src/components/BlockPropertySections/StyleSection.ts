import BackgroundHandler from "@/components/BackgroundHandler.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";

const styleSectionProperties = [
	{
		component: ColorInput,
		getProps: () => {
			return {
				label: "BG Color",
				value: blockController.getStyle("background"),
			};
		},
		searchKeyWords: "Background, BackgroundColor, Background Color, BG, BGColor, BG Color",
		events: {
			change: (val: StyleValue) => blockController.setStyle("background", val),
		},
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
		component: InlineInput,
		getProps: () => {
			return {
				label: "Border Width",
				modelValue: blockController.getStyle("borderWidth"),
				enableSlider: true,
				unitOptions: ["px", "%", "em", "rem"],
				minValue: 0,
			};
		},
		searchKeyWords: "Border, Width, BorderWidth, Border Width",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("borderWidth", val),
		},
		condition: () => blockController.getStyle("borderColor") || blockController.getStyle("borderWidth"),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Border Style",
				modelValue: blockController.getStyle("borderStyle"),
				type: "select",
				options: [
					{
						value: "solid",
						label: "Solid",
					},
					{
						value: "dashed",
						label: "Dashed",
					},
					{
						value: "dotted",
						label: "Dotted",
					},
				],
			};
		},
		searchKeyWords: "Border, Style, BorderStyle, Border Style, Solid, Dashed, Dotted",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("borderStyle", val),
		},
		condition: () => blockController.getStyle("borderColor"),
	},
	{
		component: BackgroundHandler,
		getProps: () => {},
		searchKeyWords:
			"Background, BackgroundImage, Background Image, Background Position, Background Repeat, Background Size, BG, BGImage, BG Image, BGPosition, BG Position, BGRepeat, BG Repeat, BGSize, BG Size",
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Shadow",
				type: "select",
				options: [
					{
						value: null,
						label: "None",
					},
					{
						label: "Small",
						value:
							"rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.05) 0px 1px 2px 0px, rgba(0, 0, 0, 0.05) 0px 1px 3px 0px",
					},
					{
						label: "Medium",
						value:
							"rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 10px 15px -3px, rgba(0, 0, 0, 0.1) 0px 4px 6px -4px",
					},
					{
						label: "Large",
						value:
							"rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0) 0px 0px 0px 0px, rgba(0, 0, 0, 0.1) 0px 20px 25px -5px, rgba(0, 0, 0, 0.1) 0px 10px 10px -5px",
					},
				],
				modelValue: blockController.getStyle("boxShadow"),
			};
		},
		searchKeyWords: "Shadow, BoxShadow, Box Shadow",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("boxShadow", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Radius",
				modelValue: blockController.getStyle("borderRadius"),
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
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Z-Index",
				modelValue: blockController.getStyle("zIndex"),
			};
		},
		searchKeyWords: "Z, Index, ZIndex, Z Index",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("zIndex", val),
		},
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
