import Autocomplete from "@/components/Controls/Autocomplete.vue";
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import FontUploader from "@/components/Controls/FontUploader.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import userFonts from "@/data/userFonts";
import { UserFont } from "@/types/doctypes";
import { filterOptions } from "@/utils/autocompleteOptions";
import blockController from "@/utils/blockController";
import { setFont as _setFont, fontListItems, getFontWeightOptions, loadFontList } from "@/utils/fontManager";
import { BOX_UNIT_OPTIONS } from "@/utils/unitOptions";

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
				label: "Content",
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
				label: "Family",
				component: Autocomplete,
				propertyKey: "fontFamily",
				getOptions: async (filterString: string) => {
					await loadFontList();
					const toOption = (family: string) => ({ label: family, value: family });
					const userFontOptions = filterOptions(
						(userFonts.data || []).map((font: UserFont) => toOption(font.font_name as string)),
						filterString,
						{ limit: 10, windowRadius: { upper: 4, lower: 5 } },
					);
					const defaultFontOptions = filterOptions(
						fontListItems.value.map((font) => toOption(font.family)),
						filterString,
						{ limit: 20, windowRadius: { upper: 4, lower: 15 } },
					);

					if (!userFontOptions.length) return defaultFontOptions;
					return [
						{ label: "Custom", value: "_separator_1" },
						...userFontOptions,
						{ label: "Default", value: "_separator_2" },
						...defaultFontOptions,
					];
				},
				actionButton: {
					component: FontUploader,
				},
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
				label: "Weight",
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
				label: "Size",
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
				label: "Height",
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
				label: "Letter",
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
				label: "Transform",
				propertyKey: "textTransform",
				type: "select",
				options: [
					{
						value: "unset",
						label: "Unset",
					},
					{
						value: "uppercase",
						label: "Uppercase",
					},
					{
						value: "lowercase",
						label: "Lowercase",
					},
					{
						value: "capitalize",
						label: "Capitalize",
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
				label: "Align",
				propertyKey: "textAlign",
				component: OptionToggle,
				options: [
					{
						label: "Left",
						value: "left",
						icon: "lucide-align-left",
						hideLabel: true,
					},
					{
						label: "Center",
						value: "center",
						icon: "lucide-align-center",
						hideLabel: true,
					},
					{
						label: "Right",
						value: "right",
						icon: "lucide-align-right",
						hideLabel: true,
					},
					{
						label: "Justify",
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
	name: "Typography",
	properties: typographySectionProperties,
	condition: () => blockController.isText() || blockController.isContainer() || blockController.isInput(),
};
