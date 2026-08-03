import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import { computed } from "vue";

const accessibilitySectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "标签",
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
		getProps: () => ({
			label: "Aria 标签",
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
			label: "角色",
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
			label: "Tab 索引",
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
	name: "无障碍",
	properties: accessibilitySectionProperties,
	collapsed: computed(
		() =>
			!blockController.getAttribute("aria-label") &&
			!blockController.getAttribute("role") &&
			!blockController.getAttribute("tabindex"),
	),
};
