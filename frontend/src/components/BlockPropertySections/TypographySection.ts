import Autocomplete from "@/components/Controls/Autocomplete.vue";
import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import FontUploader from "@/components/Controls/FontUploader.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import StylePropertyControl from "@/components/Controls/StylePropertyControl.vue";
import userFonts from "@/data/userFonts";
import { UserFont } from "@/types/Builder/UserFont";
import blockController from "@/utils/blockController";
import { setFont as _setFont, fontList, getFontWeightOptions } from "@/utils/fontManager";
import stylePreset from "@/data/stylePreset";

const setFont = (font: string) => {
	_setFont(font, null).then(() => {
		blockController.setFontFamily(font);
	});
};

const styleKeyMap: Record<string, string> = {
    fontFamily: "fontFamily",
    fontWeight: "fontWeight",
    fontSize: "fontSize",
    lineHeight: "lineHeight",
    transform: "textTransform",
};

const typographySectionProperties = [
	{
		component: BasePropertyControl,
		getProps: () => {
			return {
				label: "Content",
				propertyKey: "innerHTML",
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
				label: "Style",
				propertyKey: "textStylePreset",
				type: "select",
				options: stylePreset.data //list of items in dropdown
					? [
						{ label: "None", value: null },
						...stylePreset.data.map((s: any) => ({ //s -> object and kept any not defined type of it 
						label: s.style_name, //if stylebook.data exists and loaded, do the map or else return empty array
						value: s.style_name,
					}))
					]	
					: [{ label: "None", value: " " }],
				getModelValue: () => String(blockController.getStyle("textStylePreset") ?? ""),
				setModelValue: (val: string) => { //called when user selects an option
					blockController.setStyle("textStylePreset", val);
					blockController.setPresetStyle(val);
					if (!val) {
						blockController.setPresetStyle("");
						Object.values(styleKeyMap).forEach((cssProperty) => {
            				blockController.setStyle(cssProperty as styleProperty, null);
          	        });
        			return;
					}
					const preset = stylePreset.data?.find((s: any) => s.style_name === val);
					if (!preset) return;
					const map = typeof preset.style_map === "string" 
    					? JSON.parse(preset.style_map) 	
						: preset.style_map;
					Object.entries(map).forEach(([key, value]) => {
					if (key === "fontFamily") {
						setFont(value as string);
					} else if (styleKeyMap[key]) {
						blockController.setStyle(styleKeyMap[key] as styleProperty, value as string);
					}
				});
			},
			};
		},
		searchKeyWords: "Style, Preset, Typography",
		condition: () => blockController.isText(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {

			const presetName = blockController.getPresetStyle();

			const preset = stylePreset.data?.find((s: any) => s.style_name === presetName);

			const presetMap = preset
				? (typeof preset.style_map === "string" ? JSON.parse(preset.style_map) : preset.style_map)
				: null;

			const isInherited = presetMap && blockController.getNativeStyle("fontFamily") === presetMap.fontFamily;

			return {
				label: "Family",
				component: Autocomplete,
				propertyKey: "fontFamily",
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
				getModelValue: () => isInherited ? "" : String(blockController.getNativeStyle("fontFamily") ?? ""),
				getPlaceholder: () => presetMap?.fontFamily
				? String(presetMap.fontFamily) 
				: String(blockController.getCascadingStyle("fontFamily") ?? "unset"),
				setModelValue: (val: string) => {
					if(!val && presetMap?.fontFamily) {
						blockController.setStyle("fontFamily", presetMap.fontFamily)
					} 
					else{
						blockController.setStyle("fontFamily", val);
					}
				},
			};
		},
		searchKeyWords: "Font, Family, FontFamily",
		condition: () => blockController.isText() || blockController.isContainer(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {

			const presetName = blockController.getPresetStyle();

			const preset = stylePreset.data?.find((s: any) => s.style_name === presetName);

			const presetMap = preset 
				? (typeof preset.style_map === "string" ? JSON.parse(preset.style_map) : preset.style_map) 
				: null;

			const isInherited = presetMap && blockController.getNativeStyle("fontWeight") === presetMap.fontWeight;

			return {
				label: "Weight",
				propertyKey: "fontWeight",
				component: Autocomplete,
				options: getFontWeightOptions((blockController.getStyle("fontFamily") || "Inter") as string),
				getModelValue: () => isInherited ? "" : String(blockController.getNativeStyle("fontWeight") ?? ""),
				getPlaceholder: () => presetMap?.fontWeight
				? String(presetMap.fontWeight) 
				: String(blockController.getCascadingStyle("fontWeight") ?? "unset"),
				setModelValue: (val: string) => {
					if(!val && presetMap?.fontWeight) {
						blockController.setStyle("fontWeight", presetMap.fontWeight)
					} 
					else{
						blockController.setStyle("fontWeight", val);
					}
				},
			};
		},
		searchKeyWords: "Font, Weight, FontWeight",
	},
	{
		component: StylePropertyControl,
		getProps: () => {

			// check if a preset is active
			const presetName = blockController.getPresetStyle();
			
			// find that preset's data
			const preset = stylePreset.data?.find((s: any) => s.style_name === presetName);
			
			// get the preset's style map , without this can get undefined so added check for it too
			const presetMap = preset 
				? (typeof preset.style_map === "string" //preset exists get the map
				? JSON.parse(preset.style_map) // if string, parse it into object
				: preset.style_map) //if already object, use as is
				: null;
			
			// check if fontSize is still matching the preset value (not manually changed)
			const isInherited = presetMap && blockController.getNativeStyle("fontSize") === presetMap.fontSize;

			return {
				label: "Size",
				propertyKey: "fontSize",
				enableSlider: true,
				minValue: 1,
				unitOptions: ["px", "em", "rem"],
				getModelValue: () => isInherited ? "" : String(blockController.getNativeStyle("fontSize") ?? ""),
				getPlaceholder: () => presetMap?.fontSize 
				? String(presetMap.fontSize) 
				: String(blockController.getCascadingStyle("fontSize") ?? "unset"),
        		setModelValue: (val: string) => {
					if(!val && presetMap?.fontSize) {
						blockController.setStyle("fontSize", presetMap.fontSize)
					} 
					else{
						blockController.setStyle("fontSize", val);
					}
				},
			};
		},
		searchKeyWords: "Font, Size, FontSize",
		condition: () => blockController.isText() || blockController.isInput(),
	},
	{
		component: StylePropertyControl,
		getProps: () => {

			const presetName = blockController.getPresetStyle();

			const preset = stylePreset.data?.find((s: any) => s.style_name === presetName);

			const presetMap = preset
				? (typeof preset.style_map === "string" ? JSON.parse(preset.style_map) : preset.style_map)
				: null;

			const isInherited = presetMap && blockController.getNativeStyle("lineHeight") === presetMap.lineHeight;

			return {
				label: "Height",
				propertyKey: "lineHeight",
				getModelValue: () => isInherited ? "" : String(blockController.getNativeStyle("lineHeight") ?? ""),
				getPlaceholder: () => presetMap?.lineHeight
                ? String(presetMap.lineHeight)
                : String(blockController.getCascadingStyle("lineHeight") ?? "unset"),
				setModelValue: (val: string) => {
					if (!val && presetMap?.lineHeight) {
						blockController.setStyle("lineHeight", presetMap.lineHeight);
					} 
					else {
						blockController.setStyle("lineHeight", val);
					}
				},
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
