import BackgroundHandler from "@/components/BackgroundHandler.vue";
import ColorInput from "@/components/Controls/ColorInput.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { BORDER_UNIT_OPTIONS, RADIUS_UNIT_OPTIONS, ROTATION_UNIT_OPTIONS } from "@/utils/unitOptions";
import RangeInput from "../Controls/RangeInput.vue";
import ShadowHandler from "@/components/ShadowHandler.vue";
import SplitPropertyControl from "@/components/Controls/SplitPropertyControl.vue";
import { __ } from "@/translation";

const hasBorder = () =>
	Boolean(blockController.getStyle("borderColor") || blockController.getStyle("borderWidth"));

const overflowOptions = [
	{
		label: __("Unset"),
		value: "unset",
	},
	{
		label: __("Auto"),
		value: "auto",
	},
	{
		label: __("Visible"),
		value: "visible",
	},
	{
		label: __("Hidden"),
		value: "hidden",
	},
	{
		label: __("Scroll"),
		value: "scroll",
	},
];

const styleSectionProperties = [
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Opacity"),
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
		usedStyleProperties: [
			"background",
			"background-attachment",
			"background-blend-mode",
			"background-clip",
			"background-color",
			"background-image",
			"background-origin",
			"background-position",
			"background-repeat",
			"background-size",
		],
		searchKeyWords:
			"Background, BackgroundImage, Background Image, Background Position, Background Repeat, Background Size, BG, BGImage, BG Image, BGPosition, BG Position, BGRepeat, BG Repeat, BGSize, BG Size",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				propertyKey: "color",
				component: ColorInput,
				label: __("Text Color"),
				popoverOffset: 120,
			};
		},
		searchKeyWords: "Text, Color, TextColor, Text Color",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Border Color"),
				propertyKey: "borderColor",
				component: ColorInput,
				popoverOffset: 120,
				events: {
					// a border only shows up once it has a width and a style
					"update:modelValue": (value: StyleValue) => {
						if (!value) {
							blockController.setStyle("borderWidth", null);
							blockController.setStyle("borderStyle", null);
						} else if (!blockController.getStyle("borderWidth")) {
							blockController.setStyle("borderWidth", "1px");
							blockController.setStyle("borderStyle", "solid");
						}
					},
				},
			};
		},
		usedStyleProperties: ["border", "border-color"],
		searchKeyWords: "Border, Color, BorderColor, Border Color",
	},
	{
		component: SplitPropertyControl,
		getProps: () => {
			return {
				label: __("Border Width"),
				propertyKey: "borderWidth",
				unitOptions: BORDER_UNIT_OPTIONS,
				splits: ["T", "R", "B", "L"],
				toModelValue: (parts: StyleValue[]) => parts.join(" "),
				getModelValue: (state: string | null = null) =>
					String(blockController.getStyle(state ? `${state}:borderWidth` : "borderWidth") || ""),
			};
		},
		usedStyleProperties: ["border-width"],
		searchKeyWords: "Border, Width, BorderWidth, Border Width",
		condition: () => hasBorder(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Border Style"),
				propertyKey: "borderStyle",
				type: "select",
				options: [
					{ value: "solid", label: __("Solid") },
					{ value: "dashed", label: __("Dashed") },
					{ value: "dotted", label: __("Dotted") },
				],
			};
		},
		usedStyleProperties: ["border-style"],
		searchKeyWords: "Border, Style, BorderStyle, Border Style",
		condition: () => hasBorder(),
	},
	{
		component: ShadowHandler,
		getProps: () => {},
		usedStyleProperties: ["box-shadow"],
		searchKeyWords: "Shadow, BoxShadow, Box Shadow",
	},
	{
		component: SplitPropertyControl,
		getProps: () => {
			return {
				label: __("Radius"),
				placeholder: __("None"),
				propertyKey: "borderRadius",
				unitOptions: RADIUS_UNIT_OPTIONS,
				splits: ["TL", "TR", "BR", "BL"],
				getModelValue: (state: string | null = null) =>
					String(blockController.getStyle(state ? `${state}:borderRadius` : "borderRadius") || ""),
			};
		},
		events: {
			// rounded corners only show if the content is clipped
			"update:modelValue": (value: StyleValue) => {
				if (!value) return;
				if (!blockController.getStyle("overflowX")) blockController.setStyle("overflowX", "hidden");
				if (!blockController.getStyle("overflowY")) blockController.setStyle("overflowY", "hidden");
			},
		},
		usedStyleProperties: [
			"border-bottom-left-radius",
			"border-bottom-right-radius",
			"border-radius",
			"border-top-left-radius",
			"border-top-right-radius",
		],
		searchKeyWords: "Border, Radius, BorderRadius, Border Radius",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Z-Index"),
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
				label: __("Overflow X"),
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
				label: __("Overflow Y"),
				propertyKey: "overflowY",
				type: "select",
				options: overflowOptions,
				setModelValue: (val: StyleValue) => {
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
				label: __("Cursor"),
				propertyKey: "cursor",
				type: "select",
				options: [
					{ value: null, label: __("Default") },
					{ value: "pointer", label: __("Pointer") },
					{ value: "move", label: __("Move") },
					{ value: "text", label: __("Text") },
					{ value: "crosshair", label: __("Crosshair") },
					{ value: "not-allowed", label: __("Not Allowed") },
				],
			};
		},
		searchKeyWords: "Cursor, Pointer, Move, Text, Crosshair, NotAllowed, Not Allowed",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Rotation"),
				propertyKey: "rotate",
				enableSlider: true,
				unitOptions: ROTATION_UNIT_OPTIONS,
				minValue: -360,
				maxValue: 360,
				defaultValue: 0,
			};
		},
		searchKeyWords: "Rotation, Rotate, Angle, Degrees",
		condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	},
];

export default {
	name: __("Style"),
	properties: styleSectionProperties,
};
