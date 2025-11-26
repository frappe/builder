import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const accessibilitySectionProperties = [
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
					"form",
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
		condition: () => !blockController.isRoot(),
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
		getProps: () => ({
			label: "Aria Label",
			modelValue: blockController.getAttribute("aria-label"),
		}),
		searchKeyWords: "AriaLabel, Aria Label, Label, Accessibility Label, Aria",
		events: {
			"update:modelValue": (val: string) =>
				val?.trim()
					? blockController.setAttribute("aria-label", val.trim())
					: blockController.removeAttribute("aria-label"),
		},
	},
	{
		component: InlineInput,
		getProps: () => ({
			label: "Role",
			type: "select",
			options: [
				"button",
				"alert",
				"link",
				"navigation",
				"banner",
				"main",
				"contentinfo",
				"heading",
				"form",
				"list",
				"table",
				"text",
				"alertdialog",
				"tab",
				"tabpanel",
				"presentation",
				"region",
			],
			modelValue: blockController.getAttribute("role"),
		}),
		searchKeyWords: "Role, Accessibility, AccessibilityRole, Accessibility Role",
		events: {
			"update:modelValue": (val: string) => {
				blockController.setAttribute("role", val);
			},
		},
	},
	{
		component: InlineInput,
		getProps: () => ({
			label: "Tab Index",
			type: "number",
			min: -1,
			modelValue: blockController.getAttribute("tabindex"),
		}),
		searchKeyWords: "TabIndex, Keyboard Focus, Focus Order, Accessibility",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("tabindex", val),
		},
	},
];

export default {
	name: "Accessibility",
	properties: accessibilitySectionProperties,
	collapsed: computed(
		() =>
			!blockController.getAttribute("aria-label") &&
			!blockController.getAttribute("role") &&
			!blockController.getAttribute("tabindex"),
	),
};
