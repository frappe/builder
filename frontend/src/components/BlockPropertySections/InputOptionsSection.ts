import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

// boolean attributes are on whenever present, whatever their value ("", "true", "required")
const hasAttribute = (attribute: string) => blockController.getEffectiveAttribute(attribute) != null;

const inputOptionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Type"),
				type: "select",
				options: [
					"text",
					"number",
					"email",
					"password",
					"date",
					"time",
					"search",
					"tel",
					"url",
					"color",
					"radio",
				],
				modelValue: blockController.getEffectiveAttribute("type") || "text",
			};
		},
		searchKeyWords:
			"Input, Type, InputType, Input Type, Text, Number, Email, Password, Date, Time, Search, Tel, Url, Color, Radio, tag",
		events: {
			"update:modelValue": (val: string) => blockController.setEffectiveAttribute("type", val),
		},
		condition: () => !blockController.isTextarea() && !blockController.isSelect(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Placeholder"),
				modelValue: blockController.getEffectiveAttribute("placeholder"),
			};
		},
		searchKeyWords:
			"Placeholder, Input, PlaceholderText, Placeholder Text, form, input, text, number, email, password, date, time, search, tel, url, color, tag",
		events: {
			"update:modelValue": (val: string) => blockController.setEffectiveAttribute("placeholder", val),
		},
		condition: () => !blockController.isSelect(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Name"),
				modelValue: blockController.getEffectiveAttribute("name") || "",
				description: __(
					"Key this field's value is submitted under. Radio buttons with the same name are grouped together.",
				),
			};
		},
		searchKeyWords:
			"Name, Field Name, FieldName, Submission, Key, Radio, Group, Group Name, form, input, textarea, select",
		events: {
			"update:modelValue": (val: string) => blockController.setEffectiveAttribute("name", val || undefined),
		},
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: __("Required"),
				options: [
					{ label: __("Yes"), value: true },
					{ label: __("No"), value: false },
				],
				modelValue: hasAttribute("required"),
			};
		},
		searchKeyWords: "Required, Mandatory, Validation, form, input, textarea, select",
		events: {
			"update:modelValue": (val: boolean) =>
				blockController.setEffectiveAttribute("required", val ? "required" : undefined),
		},
	},
	// Radio button specific properties
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Value"),
				modelValue: blockController.getAttribute("value") || "",
				description: __("Value submitted with the form when this radio button is selected."),
			};
		},
		searchKeyWords: "Radio, Value, RadioValue, Radio Value, input, radio button",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("value", val),
		},
		condition: () => blockController.getAttribute("type") === "radio",
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: __("Checked"),
				options: [
					{ label: __("Yes"), value: true },
					{ label: __("No"), value: false },
				],
				modelValue:
					blockController.getAttribute("checked") === "" ||
					blockController.getAttribute("checked") === "checked",
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
		condition: () => blockController.getAttribute("type") === "radio",
	},
];

export default {
	name: __("Input Options"),
	properties: inputOptionsSectionProperties,
	condition: () => blockController.isInput() || blockController.isSelect(),
};
