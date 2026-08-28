import Autocomplete from "@/components/Controls/Autocomplete.vue";
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import FontInput from "@/components/Controls/FontInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import blockController from "@/utils/blockController";
import { setFont as _setFont, getFontWeightOptions, loadFontList } from "@/utils/fontManager";
import { BOX_UNIT_OPTIONS } from "@/utils/unitOptions";
import { __ } from "@/translation";

const setFont = (font: string) => {
	_setFont(font, null).then(() => {
		blockController.setFontFamily(font);
	});
};

const typographySectionProperties = [
	{
		component: BasePropertyControl,
		getProps: () => {
			return {
				label: __("Content"),
				propertyKey: "innerHTML",
				controlType: "key",
				// @ts-ignore
				allowDynamicValue: true,
				getModelValue: () => blockController.getText(),
				setModelValue: (val: string) => {
					blockController.setInnerHTML(val);
				},
			};
		},
		searchKeyWords: "Content, Text, ContentText, Content Text",
		condition: () =>
			(blockController.isText() || blockController.isButton()) && !blockController.multipleBlocksSelected(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Family"),
				component: FontInput,
				propertyKey: "fontFamily",
				getModelValue: () => blockController.getFontFamily(),
				setModelValue: (val: string) => setFont(val),
			};
		},
		searchKeyWords: "Font, Family, FontFamily",
		condition: () => blockController.isText() || blockController.isContainer(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Weight"),
				propertyKey: "fontWeight",
				component: Autocomplete,
				// static options were never query-filtered, so ignore the search
				// string; awaiting the list keeps all weights of a preselected
				// font available on first open
				getOptions: async () => {
					await loadFontList();
					return getFontWeightOptions((blockController.getStyle("fontFamily") || "Inter") as string);
				},
				step: 100,
				min: 100,
				max: 900,
			};
		},
		searchKeyWords: "Font, Weight, FontWeight",
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Size"),
				propertyKey: "fontSize",
				enableSlider: true,
				minValue: 1,
				unitOptions: BOX_UNIT_OPTIONS,
			};
		},
		searchKeyWords: "Font, Size, FontSize",
		condition: () => blockController.isText() || blockController.isInput(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Height"),
				propertyKey: "lineHeight",
				enableSlider: true,
			};
		},
		searchKeyWords: "Font, Height, LineHeight, Line Height",
		condition: () => blockController.isText(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Letter"),
				propertyKey: "letterSpacing",
				enableSlider: true,
			};
		},
		searchKeyWords: "Font, Letter, LetterSpacing, Letter Spacing",
		condition: () => blockController.isText(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Transform"),
				propertyKey: "textTransform",
				type: "select",
				options: [
					{
						value: "unset",
						label: __("Unset"),
					},
					{
						value: "uppercase",
						label: __("Uppercase"),
					},
					{
						value: "lowercase",
						label: __("Lowercase"),
					},
					{
						value: "capitalize",
						label: __("Capitalize"),
					},
				],
				setModelValue: (val: string) => {
					blockController.setStyle("textTransform", val === "unset" ? null : val);
				},
			};
		},
		searchKeyWords:
			"Font, Transform, TextTransform, Text Transform, Capitalize, Uppercase, Lowercase, Unset, None",
		condition: () => blockController.isText(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {
			return {
				label: __("Align"),
				propertyKey: "textAlign",
				component: OptionToggle,
				options: [
					{
						label: __("Left"),
						value: "left",
						icon: "lucide-align-left",
						hideLabel: true,
					},
					{
						label: __("Center"),
						value: "center",
						icon: "lucide-align-center",
						hideLabel: true,
					},
					{
						label: __("Right"),
						value: "right",
						icon: "lucide-align-right",
						hideLabel: true,
					},
					{
						label: __("Justify"),
						value: "justify",
						icon: "lucide-align-justify",
						hideLabel: true,
					},
				],
				defaultValue: "left",
			};
		},
		searchKeyWords: "Font, Align, TextAlign, Text Align, Left, Center, Right, Justify",
		condition: () => blockController.isText(),
	},
];

export default {
	name: __("Typography"),
	properties: typographySectionProperties,
	condition: () => blockController.isText() || blockController.isContainer() || blockController.isInput(),
};
