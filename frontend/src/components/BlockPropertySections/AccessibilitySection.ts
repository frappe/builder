import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
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
				options: ["text", "number", "email", "password", "date", "time", "search", "tel", "url", "color", "radio"],
				modelValue: blockController.getAttribute("type") || "text",
			};
		},
		searchKeyWords:
			"Input, Type, InputType, Input Type, Text, Number, Email, Password, Date, Time, Search, Tel, Url, Color, Radio, tag",
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
	// Radio button specific properties
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Radio Group Name",
				modelValue: blockController.getAttribute("name") || "",
				description:
					"The group name for this radio button. Radio buttons with the same name are grouped together, allowing only one to be selected at a time.",
			};
		},
		searchKeyWords: "Radio, Name, Group, RadioName, Radio Name, Group Name, input, radio button",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("name", val),
		},
		condition: () =>
			blockController.getKeyValue("element") === "input" && blockController.getAttribute("type") === "radio",
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Radio Value",
				modelValue: blockController.getAttribute("value") || "",
				description:
					"The value assigned to this radio button. When selected, this value will be submitted with the form.",
			};
		},
		searchKeyWords: "Radio, Value, RadioValue, Radio Value, input, radio button",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("value", val),
		},
		condition: () =>
			blockController.getKeyValue("element") === "input" && blockController.getAttribute("type") === "radio",
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Initially Checked",
				options: [
					{ label: "Yes", value: true },
					{ label: "No", value: false },
				],
				modelValue:
					blockController.getAttribute("checked") === "" || blockController.getAttribute("checked") === "checked",
			};
		},
		searchKeyWords: "Checked, Radio, DefaultValue, Default Value, Selected, Initially Checked",
		events: {
			"update:modelValue": (val: boolean) => {
				if (val) {
					blockController.setAttribute("checked", "checked");
				} else {
					blockController.removeAttribute("checked");
				}
			},
		},
		condition: () =>
			blockController.getKeyValue("element") === "input" && blockController.getAttribute("type") === "radio",
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
