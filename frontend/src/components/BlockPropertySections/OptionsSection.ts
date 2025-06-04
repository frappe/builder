import CodeEditor from "@/components/Controls/CodeEditor.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};

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
		condition: () => !blockController.isForm(),
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
				label: "Overflow X",
				type: "select",
				options: overflowOptions,
				modelValue: blockController.getStyle("overflowX"),
			};
		},
		searchKeyWords:
			"Overflow, X, OverflowX, Overflow X, Auto, Visible, Hide, Scroll, horizontal scroll, horizontalScroll",
		events: {
			"update:modelValue": (val: StyleValue) => {
				if (val === "unset") {
					val = null;
				}
				blockController.setStyle("overflowX", val);
			},
		},
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Overflow Y",
				type: "select",
				options: overflowOptions,
				modelValue: blockController.getStyle("overflowY"),
			};
		},
		searchKeyWords:
			"Overflow, Y, OverflowY, Overflow Y, Auto, Visible, Hide, Scroll, vertical scroll, verticalScroll",
		events: {
			"update:modelValue": (val: StyleValue) => {
				if (val === "unset") {
					val = null;
				}
				blockController.setStyle("overflowY", val);
			},
		},
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
		component: CodeEditor,
		getProps: () => {
			return {
				label: "HTML",
				type: "HTML",
				autofocus: false,
				modelValue: blockController.getInnerHTML() || "",
			};
		},
		searchKeyWords: "HTML, InnerHTML, Inner HTML",
		events: {
			"update:modelValue": (val: string) => {
				blockController.setInnerHTML(val);
			},
		},
		condition: () =>
			blockController.isHTML() || (blockController.getInnerHTML() && !blockController.isText()),
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
	},
];

export default {
	name: "Options",
	properties: optionsSectionProperties,
};
