import BackgroundHandler from "@/components/BackgroundHandler.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import RangeInput from "../Controls/RangeInput.vue";

const overflowOptions = [
	{
		label: "Unset",
		value: "unset",
	},
	{
		label: "Auto",
		value: "auto",
	},
	{
		label: "Visible",
		value: "visible",
	},
	{
		label: "Hidden",
		value: "hidden",
	},
	{
		label: "Scroll",
		value: "scroll",
	},
];

const styleSectionProperties = [
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Opacity",
				propertyKey: "opacity",
				enableSlider: false,
				component: RangeInput,
				getModelValue: () => {
					return blockController.getStyle("opacity") || 1;
				},
				min: 0,
				max: 1,
				step: 0.01,
				default: 1,
			};
		},
		condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	},
	{
		component: BackgroundHandler,
		getProps: () => {},
		searchKeyWords:
			"Background, BackgroundImage, Background Image, Background Position, Background Repeat, Background Size, BG, BGImage, BG Image, BGPosition, BG Position, BGRepeat, BG Repeat, BGSize, BG Size",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				propertyKey: "color",
				component: ColorInput,
				label: "Text Color",
				popoverOffset: 120,
			};
		},
		searchKeyWords: "Text, Color, TextColor, Text Color",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				component: ColorInput,
				propertyKey: "borderColor",
				popoverOffset: 120,
				label: "Border Color",
			};
		},
		searchKeyWords: "Border, Color, BorderColor, Border Color",
		events: {
			"update:modelValue": (val: StyleValue) => {
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
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Border Width",
				propertyKey: "borderWidth",
				enableSlider: true,
				unitOptions: ["px", "%", "em", "rem"],
				minValue: 0,
			};
		},
		searchKeyWords: "Border, Width, BorderWidth, Border Width",
		condition: () => blockController.getStyle("borderColor") || blockController.getStyle("borderWidth"),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Border Style",
				propertyKey: "borderStyle",
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
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Shadow",
				propertyKey: "boxShadow",
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
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Radius",
				propertyKey: "borderRadius",
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
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Z-Index",
				propertyKey: "zIndex",
			};
		},
		searchKeyWords: "Z, Index, ZIndex, Z Index, Z-index, Z-Index",
		condition: () =>
			!blockController.multipleBlocksSelected() &&
			!blockController.isRoot() &&
			blockController.getStyle("position") !== "static",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Overflow X",
				type: "select",
				propertyKey: "overflowX",
				options: overflowOptions,
				setModelValue: (val: StyleValue) => {
					if (val === "unset") {
						val = null;
					}
					blockController.setStyle("overflowX", val);
				},
			};
		},
		searchKeyWords:
			"Overflow, X, OverflowX, Overflow X, Auto, Visible, Hide, Scroll, horizontal scroll, horizontalScroll",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Overflow Y",
				propertyKey: "overflowY",
				type: "select",
				options: overflowOptions,
				setModelValue: (val: StyleValue) => {
					console.log("Setting overflowY to", val);
					if (val === "unset") {
						val = null;
					}
					blockController.setStyle("overflowY", val);
				},
			};
		},
		searchKeyWords:
			"Overflow, Y, OverflowY, Overflow Y, Auto, Visible, Hide, Scroll, vertical scroll, verticalScroll",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: "Cursor",
				propertyKey: "cursor",
				type: "select",
				options: [
					{ value: null, label: "Default" },
					{ value: "pointer", label: "Pointer" },
					{ value: "move", label: "Move" },
					{ value: "text", label: "Text" },
					{ value: "crosshair", label: "Crosshair" },
					{ value: "not-allowed", label: "Not Allowed" },
				],
			};
		},
		searchKeyWords: "Cursor, Pointer, Move, Text, Crosshair, NotAllowed, Not Allowed",
	},
];

export default {
	name: "Style",
	properties: styleSectionProperties,
};
