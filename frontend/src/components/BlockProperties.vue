<template>
	<div v-if="blockController.isBLockSelected()" class="mt-[-10px] flex select-none flex-col gap-3 pb-16">
		<CollapsibleSection :sectionName="section.name" v-for="section in sections">
			<template v-for="property in section.properties">
				<component
					v-if="property.condition ? property.condition() : true"
					:is="property.component"
					v-bind="property.getProps()"
					v-on="property.events || {}" />
			</template>
		</CollapsibleSection>
	</div>
	<div v-else>
		<p class="text-center text-sm text-gray-600 dark:text-zinc-500">Select a block to edit properties.</p>
	</div>
</template>
<script setup lang="ts">
import { setFont as _setFont, fontListNames, getFontWeightOptions } from "@/utils/fontManager";

import BackgroundHandler from "./BackgroundHandler.vue";
import BLockLayoutHandler from "./BlockLayoutHandler.vue";
import BlockPositionHandler from "./BlockPositionHandler.vue";
import CollapsibleSection from "./CollapsibleSection.vue";
import ColorInput from "./ColorInput.vue";
import InlineInput from "./InlineInput.vue";
import ObjectEditor from "./ObjectEditor.vue";

import blockController from "@/utils/blockController";
import CodeEditor from "./CodeEditor.vue";
import DimensionInput from "./DimensionInput.vue";
import OptionToggle from "./OptionToggle.vue";

type BlockProperty = {
	component: any;
	getProps: () => Record<string, unknown>;
	events?: Record<string, unknown>;
	condition?: () => boolean;
};

type PropertySection = {
	name: string;
	properties: BlockProperty[];
	condition?: () => boolean;
};

const setFont = (font: string) => {
	_setFont(font).then(() => {
		blockController.setFontFamily(font);
	});
};

const getClasses = () => {
	return blockController.getClasses().join(", ");
};

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};

const typographySectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Family",
				type: "autocomplete",
				options: fontListNames,
				modelValue: blockController.getFontFamily(),
			};
		},
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
			};
		},
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
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("textTransform", val),
		},
		condition: () => blockController.isText(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Align",
				modelValue: blockController.getStyle("textAlign") || "left",
				type: "select",
				options: ["left", "center", "right", "justify"],
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("textAlign", val),
		},
		condition: () => blockController.isText(),
	},
];

const layoutSectionProperties = [
	{
		component: BLockLayoutHandler,
		getProps: () => {},
	},
];

const styleSectionProperties = [
	{
		component: ColorInput,
		getProps: () => {
			return {
				label: "BG Color",
				value: blockController.getStyle("background"),
			};
		},
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
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("borderWidth", val),
		},
		condition: () => blockController.getStyle("borderColor"),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Border Style",
				modelValue: blockController.getStyle("borderStyle"),
				type: "select",
				options: ["solid", "dashed", "dotted"],
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("borderStyle", val),
		},
		condition: () => blockController.getStyle("borderColor"),
	},
	{
		component: BackgroundHandler,
		getProps: () => {},
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
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("boxShadow", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Border Radius",
				modelValue: blockController.getStyle("borderRadius"),
				enableSlider: true,
				unitOptions: ["px", "%"],
				minValue: 0,
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("borderRadius", val),
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
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("zIndex", val),
		},
		condition: () =>
			!blockController.multipleBlocksSelected() &&
			!blockController.isRoot() &&
			blockController.getStyle("position") !== "static",
	},
];

const dimensionSectionProperties = [
	{
		component: DimensionInput,
		getProps: () => {
			return {
				label: "Width",
				property: "width",
			};
		},
	},
	{
		component: DimensionInput,
		getProps: () => {
			return {
				label: "Min Width",
				property: "minWidth",
			};
		},
	},
	{
		component: DimensionInput,
		getProps: () => {
			return {
				label: "Max Width",
				property: "maxWidth",
			};
		},
	},
	{
		component: DimensionInput,
		getProps: () => {
			return {
				label: "Height",
				property: "height",
			};
		},
	},
	{
		component: DimensionInput,
		getProps: () => {
			return {
				label: "Min Height",
				property: "minHeight",
			};
		},
	},
	{
		component: DimensionInput,
		getProps: () => {
			return {
				label: "Max Height",
				property: "maxHeight",
			};
		},
	},
];

const positionSectionProperties = [
	{
		component: BlockPositionHandler,
		getProps: () => {},
	},
];

const spacingSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Margin",
				modelValue: blockController.getMargin(),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setMargin(val),
		},
		condition: () => !blockController.multipleBlocksSelected() && !blockController.isRoot(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Padding",
				modelValue: blockController.getPadding(),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setPadding(val),
		},
		condition: () => !blockController.multipleBlocksSelected(),
	},
];

const optionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Link",
				modelValue: blockController.getAttribute("href"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("href", val),
		},
		condition: () => blockController.isLink(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Opens in",
				type: "select",
				options: [
					{
						value: "_self",
						label: "Same Tab",
					},
					{
						value: "_blank",
						label: "New Tab",
					},
				],
				modelValue: blockController.getAttribute("target"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("target", val),
		},
		condition: () => blockController.isLink(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Image URL",
				modelValue: blockController.getAttribute("src"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("src", val),
		},
		condition: () => blockController.isImage(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Image Fit",
				type: "select",
				options: ["fill", "contain", "cover", "none"],
				modelValue: blockController.getStyle("objectFit"),
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("objectFit", val),
		},
		condition: () => blockController.isImage(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Tag",
				type: "select",
				options: [
					"span",
					"div",
					"section",
					"button",
					"p",
					"h1",
					"h2",
					"h3",
					"a",
					"input",
					"hr",
					"form",
					"textarea",
				],
				modelValue: blockController.getKeyValue("element"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setKeyValue("element", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Input Type",
				type: "select",
				options: ["text", "number", "email", "password", "date", "time", "search", "tel", "url", "color"],
				modelValue: blockController.getAttribute("type") || "text",
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("type", val),
		},
		condition: () => blockController.isInput(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Placeholder",
				modelValue: blockController.getAttribute("placeholder"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("placeholder", val),
		},
		condition: () => blockController.isInput(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Content",
				modelValue: blockController.getTextContent(),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setKeyValue("innerHTML", val),
		},
		condition: () => blockController.isText() || blockController.isButton(),
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Visibility",
				options: [
					{
						label: "Visible",
						value: "flex",
					},
					{
						label: "Hidden",
						value: "none",
					},
				],
				modelValue: blockController.getStyle("display") || "flex",
			};
		},
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("display", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Condition",
				modelValue: blockController.getKeyValue("visibilityCondition"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setKeyValue("visibilityCondition", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Alt Text",
				modelValue: blockController.getAttribute("alt"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("alt", val),
		},
		condition: () => blockController.isImage(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Class",
				value: getClasses(),
			};
		},
		events: {
			"update:modelValue": (val: string) => setClasses(val),
		},
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		component: CodeEditor,
		getProps: () => {
			return {
				label: "HTML",
				type: "HTML",
				modelValue: blockController.getInnerHTML() || "",
			};
		},
		events: {
			"update:modelValue": (val: string) => {
				blockController.setInnerHTML(val);
			},
		},
		condition: () => blockController.isHTML(),
	},
];

const dataKeySectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Key",
				modelValue: blockController.getDataKey("key"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setDataKey("key", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Type",
				modelValue: blockController.getDataKey("type"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setDataKey("type", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Property",
				modelValue: blockController.getDataKey("property"),
			};
		},
		events: {
			"update:modelValue": (val: string) => blockController.setDataKey("property", val),
		},
	},
];

const customAttributesSectionProperties = [
	{
		component: ObjectEditor,
		getProps: () => {
			return {
				obj: blockController.getCustomAttributes() as Record<string, string>,
			};
		},
		events: {
			"update:obj": (obj: Record<string, string>) => blockController.setCustomAttributes(obj),
		},
	},
];

const rawStyleSectionProperties = [
	{
		component: ObjectEditor,
		getProps: () => {
			return {
				obj: blockController.getRawStyles() as Record<string, string>,
			};
		},
		events: {
			"update:obj": (obj: Record<string, string>) => blockController.setRawStyles(obj),
		},
	},
];

const sections = [
	{
		name: "Layout",
		properties: layoutSectionProperties,
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		name: "Style",
		properties: styleSectionProperties,
	},
	{
		name: "Typography",
		properties: typographySectionProperties,
		condition: () => blockController.isText() || blockController.isContainer(),
	},
	{
		name: "Dimension",
		properties: dimensionSectionProperties,
	},
	{
		name: "Position",
		properties: positionSectionProperties,
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		name: "Spacing",
		properties: spacingSectionProperties,
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		name: "Options",
		properties: optionsSectionProperties,
	},
	{
		name: "Data Key",
		properties: dataKeySectionProperties,
		condition: () => blockController.isBLockSelected(),
	},
	{
		name: "Custom Attributes",
		properties: customAttributesSectionProperties,
	},
	{
		name: "Raw Style",
		properties: rawStyleSectionProperties,
	},
] as PropertySection[];
</script>
