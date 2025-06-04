import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import OptionToggle from "../Controls/OptionToggle.vue";

const inputSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Type",
				type: "select",
				options: [
					{
						label: "Text",
						value: "text",
					},
					{
						label: "Number",
						value: "number",
					},
					{
						label: "Email",
						value: "email",
					},
					{
						label: "Password",
						value: "password",
					},
					{
						label: "Date",
						value: "date",
					},
					{
						label: "Time",
						value: "time",
					},
					{
						label: "Tel",
						value: "tel",
					},
					{
						label: "Url",
						value: "url",
					},
				],
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
	// name, required, autocomplete
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Name",
				modelValue: blockController.getAttribute("name"),
			};
		},
		searchKeyWords: "Name, Input, NameText, Name Text",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("name", val),
		},
		condition: () => blockController.isInput(),
	},
	{
		component: OptionToggle,
		getProps: () => {
			return {
				label: "Required",
				modelValue: blockController.getAttribute("required") === "true",
				options: [
					{
						label: "Yes",
						value: true,
					},
					{
						label: "No",
						value: false,
					},
				],
			};
		},
		searchKeyWords:
			"Required, Input, RequiredField, Required Field, form, input, text, number, email, password, date, time, search, tel, url, color",
		events: {
			"update:modelValue": (val: boolean) => blockController.setAttribute("required", val ? "true" : "false"),
		},
		condition: () => blockController.isInput(),
	},
];

export default {
	name: "Input",
	properties: inputSectionProperties,
	confirmation: () => blockController.isInput(),
	condition: () => !blockController.multipleBlocksSelected() && blockController.isInput(),
};
