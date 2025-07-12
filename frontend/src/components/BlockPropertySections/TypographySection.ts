import Autocomplete from "@/components/Controls/Autocomplete.vue";
import FontUploader from "@/components/Controls/FontUploader.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import PropertyControl from "@/components/Controls/PropertyControl.vue";
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
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Content",
				controlType: "key",
				styleProperty: "innerHTML",
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
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Family",
				component: Autocomplete,
				styleProperty: "fontFamily",
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
				getModelValue: () => blockController.getFontFamily(),
				setModelValue: (val: string) => setFont(val),
			};
		},
		searchKeyWords: "Font, Family, FontFamily",
		condition: () => blockController.isText() || blockController.isContainer(),
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Weight",
				styleProperty: "fontWeight",
				component: Autocomplete,
				options: getFontWeightOptions((blockController.getStyle("fontFamily") || "Inter") as string),
			};
		},
		searchKeyWords: "Font, Weight, FontWeight",
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Size",
				styleProperty: "fontSize",
				enableSlider: true,
				minValue: 1,
			};
		},
		searchKeyWords: "Font, Size, FontSize",
		condition: () => blockController.isText() || blockController.isInput(),
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Height",
				styleProperty: "lineHeight",
			};
		},
		searchKeyWords: "Font, Height, LineHeight, Line Height",
		condition: () => blockController.isText(),
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Letter",
				styleProperty: "letterSpacing",
			};
		},
		searchKeyWords: "Font, Letter, LetterSpacing, Letter Spacing",
		condition: () => blockController.isText(),
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Transform",
				styleProperty: "textTransform",
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
		condition: () => blockController.isText(),
	},
	{
		component: PropertyControl,
		getProps: () => {
			return {
				label: "Align",
				styleProperty: "textAlign",
				component: OptionToggle,
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
