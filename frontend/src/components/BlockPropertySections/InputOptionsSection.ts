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
				options: ["text", "number", "email", "password", "date", "time", "search", "tel", "url", "color"],
				modelValue: blockController.getEffectiveAttribute("type") || "text",
			};
		},
		searchKeyWords:
			"Input, Type, InputType, Input Type, Text, Number, Email, Password, Date, Time, Search, Tel, Url, Color, tag",
		events: {
			"update:modelValue": (val: string) => blockController.setEffectiveAttribute("type", val),
		},
		// checkboxes and radios come from the Checkbox and Radio Group templates, with their label text
		condition: () =>
			!blockController.isTextarea() && !blockController.isSelect() && !blockController.isCheckable(),
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
		condition: () => !blockController.isSelect() && !blockController.isCheckable(),
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
		// a radio is required with its whole group, which has its own toggle
		condition: () => !blockController.isRadio(),
	},
	// Radio button and checkbox specific properties
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Value"),
				modelValue: blockController.getEffectiveAttribute("value") || "",
				description: __("Value submitted with the form when this field is checked."),
			};
		},
		searchKeyWords: "Radio, Checkbox, Value, RadioValue, Radio Value, input, radio button",
		events: {
			"update:modelValue": (val: string) => blockController.setEffectiveAttribute("value", val || undefined),
		},
		condition: () => blockController.isCheckable(),
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
				modelValue: hasAttribute("checked"),
			};
		},
		searchKeyWords: "Checked, Radio, Checkbox, DefaultValue, Default Value, Selected, Initially Checked",
		events: {
			"update:modelValue": (val: boolean) =>
				blockController.setEffectiveAttribute("checked", val ? "checked" : undefined),
		},
		condition: () => blockController.isCheckable(),
	},
];

export default {
	name: __("Input Options"),
	properties: inputOptionsSectionProperties,
	condition: () => blockController.isInput() || blockController.isSelect(),
};
