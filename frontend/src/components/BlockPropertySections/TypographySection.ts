import FontUploader from "@/components/Controls/FontUploader.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import userFonts from "@/data/userFonts";
import { UserFont } from "@/types/Builder/UserFont";
import blockController from "@/utils/blockController";
import { setFont as _setFont, fontList, getFontWeightOptions } from "@/utils/fontManager";

const setFont = (font: string) => {
	_setFont(font, null).then(() => {
		blockController.setFontFamily(font);
	});
};

const typographySectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Family",
				type: "autocomplete",
				getOptions: (filterString: string) => {
					const fontOptions = [] as { label: string; value: string }[];
					userFonts.data.forEach((font: UserFont) => {
						if (fontOptions.length >= 20) {
							return;
						}
						const fontName = font.font_name as string;
						if (fontName.toLowerCase().includes(filterString.toLowerCase()) || !filterString) {
							fontOptions.push({
								label: fontName,
								value: fontName,
							});
						}
					});
					if (fontOptions.length) {
						fontOptions.unshift({
							label: "Custom",
							value: "_separator_1",
						});
						fontOptions.push({
							label: "Default",
							value: "_separator_2",
						});
					}
					fontList.items.forEach((font) => {
						if (fontOptions.length >= 20) {
							return;
						}
						if (font.family.toLowerCase().includes(filterString.toLowerCase()) || !filterString) {
							fontOptions.push({
								label: font.family,
								value: font.family,
							});
						}
					});
					return fontOptions;
				},
				actionButton: {
					component: FontUploader,
				},
				modelValue: blockController.getFontFamily(),
			};
		},
		searchKeyWords: "Font, Family, FontFamily",
		events: {
			"update:modelValue": (val: string) => setFont(val),
		},
		condition: () => blockController.isText() || blockController.isContainer(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Weight",
				modelValue: blockController.getStyle("fontWeight"),
				type: "autocomplete",
				options: getFontWeightOptions((blockController.getStyle("fontFamily") || "Inter") as string),
			};
		},
		searchKeyWords: "Font, Weight, FontWeight",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("fontWeight", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Size",
				modelValue: blockController.getStyle("fontSize"),
				enableSlider: true,
				minValue: 1,
			};
		},
		searchKeyWords: "Font, Size, FontSize",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("fontSize", val),
		},
		condition: () => blockController.isText() || blockController.isInput(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Height",
				modelValue: blockController.getStyle("lineHeight"),
			};
		},
		searchKeyWords: "Font, Height, LineHeight, Line Height",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("lineHeight", val),
		},
		condition: () => blockController.isText(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Letter",
				modelValue: blockController.getStyle("letterSpacing"),
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("letterSpacing", val),
		},
		searchKeyWords: "Font, Letter, LetterSpacing, Letter Spacing",
		condition: () => blockController.isText(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Transform",
				modelValue: blockController.getStyle("textTransform"),
				type: "select",
				options: [
					{
						value: null,
						label: "None",
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
			};
		},
		searchKeyWords: "Font, Transform, TextTransform, Text Transform, Capitalize, Uppercase, Lowercase",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("textTransform", val),
		},
		condition: () => blockController.isText(),
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Align",
				options: [
					{
						label: "Left",
						value: "left",
						icon: "align-left",
						hideLabel: true,
					},
					{
						label: "Center",
						value: "center",
						icon: "align-center",
						hideLabel: true,
					},
					{
						label: "Right",
						value: "right",
						icon: "align-right",
						hideLabel: true,
					},
				],
				modelValue: blockController.getStyle("textAlign") || "left",
			};
		},
		searchKeyWords: "Font, Align, TextAlign, Text Align, Left, Center, Right, Justify",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("textAlign", val),
		},
		condition: () => blockController.isText(),
	},
];

export default {
	name: "Typography",
	properties: typographySectionProperties,
	condition: () => blockController.isText() || blockController.isContainer() || blockController.isInput(),
};
