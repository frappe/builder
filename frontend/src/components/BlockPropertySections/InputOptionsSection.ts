import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import SelectOptionsInput from "@/components/Controls/SelectOptionsInput.vue";
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
		// checkboxes come from the Checkbox template, with their label text
		condition: () =>
			!blockController.isTextarea() && !blockController.isSelect() && !blockController.isCheckbox(),
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
		condition: () => !blockController.isSelect() && !blockController.isCheckbox(),
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
	{
		component: SelectOptionsInput,
		getProps: () => {
			const select = blockController.getFirstSelectedBlock();
			// a component update rebuilds an instance's options from the component, keeping only renames
			const inComponent = select.isExtendedFromComponent();
			return {
				label: __("Options"),
				options: select.getOptionLabels(),
				renameOnly: inComponent,
				description: inComponent ? __("Add or remove options in the component, with Edit Component.") : "",
			};
		},
		searchKeyWords: "Options, Choices, Items, Select, Dropdown, Placeholder",
		events: {
			rename: (index: number, label: string) =>
				blockController.getFirstSelectedBlock().renameOption(index, label),
			remove: (index: number) => blockController.getFirstSelectedBlock().removeOption(index),
			add: (label: string, index?: number) => blockController.getFirstSelectedBlock().addOption(label, index),
		},
		// each select has its own options, so they are edited one select at a time
		condition: () => blockController.isSelect() && !blockController.multipleBlocksSelected(),
	},
	{
		component: InlineInput,
		getProps: () => {
			const select = blockController.getFirstSelectedBlock();
			return {
				label: __("Default"),
				type: "select",
				options: select.getOptionLabels().map((label, index) => ({ label, value: String(index) })),
				modelValue: String(select.getSelectedOptionIndex()),
				description: __("The option shown before the visitor picks one."),
			};
		},
		searchKeyWords: "Default, Default Value, Selected, Initial, Option, Select, Dropdown, Placeholder",
		events: {
			"update:modelValue": (index: string) =>
				blockController.getFirstSelectedBlock().setSelectedOption(Number(index)),
		},
		condition: () => blockController.isSelect() && !blockController.multipleBlocksSelected(),
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
		condition: () =>
			blockController.isCheckbox() || blockController.getEffectiveAttribute("type") === "radio",
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
		condition: () =>
			blockController.isCheckbox() || blockController.getEffectiveAttribute("type") === "radio",
	},
];

export default {
	name: __("Input Options"),
	properties: inputOptionsSectionProperties,
	condition: () => blockController.isInput() || blockController.isSelect(),
};
