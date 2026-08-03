import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import blockController from "@/utils/blockController";

const inputOptionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "类型",
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
				label: "占位符",
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
				label: "名称",
				modelValue: blockController.getAttribute("name") || "",
				description:
					"该单选按钮的分组名称。具有相同名称的单选按钮会被归为一组。",
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
				label: "值",
				modelValue: blockController.getAttribute("value") || "",
				description: "选中此单选按钮时随表单提交的值。",
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
				label: "已选中",
				options: [
					{ label: "是", value: true },
					{ label: "否", value: false },
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
	name: "输入选项",
	properties: inputOptionsSectionProperties,
	condition: () => blockController.isInput(),
};

