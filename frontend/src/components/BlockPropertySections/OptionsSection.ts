import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import OptionToggle from "../Controls/OptionToggle.vue";

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};

const optionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Tag",
				type: "select",
				options: [
					"aside",
					"article",
					"span",
					"div",
					"section",
					"button",
					"p",
					"a",
					"input",
					"hr",
					"textarea",
					"nav",
					"header",
					"footer",
					"label",
					"select",
					"option",
					"blockquote",
					"cite",
					"canvas",
				],
				modelValue: blockController.getKeyValue("element"),
			};
		},
		searchKeyWords:
			"Tag, Element, TagName, Tag Name, ElementName, Element Name, header, footer, nav, input, form, textarea, button, p, a, div, span, section, hr, TagType, Tag Type, ElementType, Element Type",
		events: {
			"update:modelValue": (val: string) => blockController.setKeyValue("element", val),
		},
		condition: () => !blockController.isRoot() && !blockController.isForm(),
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
		searchKeyWords:
			"Input, Type, InputType, Input Type, Text, Number, Email, Password, Date, Time, Search, Tel, Url, Color, tag",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("type", val),
		},
		condition: () => blockController.isInput(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Content",
				// @ts-ignore
				modelValue: blockController.getSelectedBlocks()[0]?.__proto__?.editor?.getText(),
			};
		},
		searchKeyWords: "Content, Text, ContentText, Content Text",
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
		searchKeyWords: "Visibility, Display, Visible, Hidden, Flex, None, hide, show",
		events: {
			"update:modelValue": (val: StyleValue) => blockController.setStyle("display", val),
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Placeholder",
				modelValue: blockController.getAttribute("placeholder"),
			};
		},
		searchKeyWords:
			"Placeholder, Input, PlaceholderText, Placeholder Text, form, input, text, number, email, password, date, time, search, tel, url, color, tag",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("placeholder", val),
		},
		condition: () => blockController.isInput(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Class",
				modelValue: blockController.getClasses().join(", "),
			};
		},
		searchKeyWords: "Class, ClassName, Class Name",
		events: {
			"update:modelValue": (val: string) => setClasses(val || ""),
		},
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Condition",
				modelValue: blockController.getKeyValue("visibilityCondition"),
				description:
					"Visibility condition to show/hide the block based on a condition. Pass a boolean variable created in your Data Script.<br><b>Note:</b> This is only evaluated in the preview mode.",
			};
		},
		searchKeyWords:
			"Condition, Visibility, VisibilityCondition, Visibility Condition, show, hide, display, hideIf, showIf",
		events: {
			"update:modelValue": (val: string) => blockController.setKeyValue("visibilityCondition", val),
		},
		condition: () => !blockController.isRoot(),
	},
];

export default {
	name: "Options",
	properties: optionsSectionProperties,
};
