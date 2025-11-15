import Input from "@/components/Controls/Input.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";

const accessibilitySectionProperties = [
	{
		component: Input,
		getProps: () => ({
			label: "Label Text (Aria-Label)",
			placeholder: "Custom label for accessibility",
			modelValue: blockController.getAttribute("aria-label"),
		}),
		searchKeyWords: "AriaLabel, Aria Label, Label, Accessibility Label, Aria",
		events: {
			"update:modelValue": (val: string) =>
				blockController.setAttribute("aria-label", val),
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
				"region"
			],
			modelValue: blockController.getAttribute("role"),
		}),
		searchKeyWords: "Role, Accessibility, AccessibilityRole, Accessibility Role",
		events: {
			"update:modelValue": (val: string) => {
				blockController.setAttribute("role", val);
			}

			
		},

		
	},

	{
		component: InlineInput,
		getProps: () => ({
			label: "Tab Index",
			type: "select",
			options: [
			  { label: "Default (0)", value: "0" },
			  { label: "Skip Focus (-1)", value: "-1" },
			  { label: "Custom Focus (1)", value: "1" },
			],
			modelValue: blockController.getAttribute("tabindex"),
		}),
		searchKeyWords: "TabIndex, Keyboard Focus, Focus Order, Accessibility",
		events: {
			"update:modelValue": (val: string) =>
				blockController.setAttribute("tabindex", val),
		},
	},
];


export default {
	name: "Accessibility",
	properties: accessibilitySectionProperties,
};
