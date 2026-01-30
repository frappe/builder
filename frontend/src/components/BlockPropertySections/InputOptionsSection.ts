import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";

const inputOptionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Type",
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
	},
	// Radio button specific properties
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Name",
				modelValue: blockController.getAttribute("name") || "",
				description:
					"Group name for this radio button. Radio buttons with the same name are grouped together.",
			};
		},
		searchKeyWords: "Radio, Name, Group, RadioName, Radio Name, Group Name, input, radio button",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("name", val),
		},
		condition: () => blockController.getAttribute("type") === "radio",
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Value",
				modelValue: blockController.getAttribute("value") || "",
				description: "Value submitted with the form when this radio button is selected.",
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
				label: "Checked",
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
		condition: () => blockController.getAttribute("type") === "radio",
	},
];

export default {
	name: "Input Options",
	properties: inputOptionsSectionProperties,
	condition: () => blockController.isInput(),
};

