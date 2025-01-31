import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";

const formOptionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Action",
				modelValue: blockController.getAttribute("action"),
			};
		},
		searchKeyWords: "Action, URL",
		events: {
			"update:modelValue": (val: string) => blockController.setAttribute("action", val),
		},
	},
] as BlockProperty[];

export default {
	name: "Form Options",
	properties: formOptionsSectionProperties,
	condition: () => blockController.isForm(),
};
