import CodeEditor from "@/components/Controls/CodeEditor.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import PropertyControl from "../Controls/PropertyControl.vue";

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};

const optionsSectionProperties = [

	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Class",
				modelValue: blockController.getClasses().join(", "),
			};
		},
		searchKeyWords: "Class, ClassName, Class Name",
		events: {
			"update:modelValue": (val: string) => setClasses(val || ""),
		},
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "Condition",
				modelValue: blockController.getKeyValue("visibilityCondition"),
				description:
					"Visibility condition to show/hide the block based on a condition. Pass a boolean variable created in your Data Script.<br><b>Note:</b> This is only evaluated in the preview mode.",
			};
		},
		searchKeyWords:
			"Condition, Visibility, VisibilityCondition, Visibility Condition, show, hide, display, hideIf, showIf",
		events: {
			"update:modelValue": (val: string) => blockController.setKeyValue("visibilityCondition", val),
		},
		condition: () => !blockController.isRoot(),
	},
];

export default {
	name: "Options",
	properties: optionsSectionProperties,
};
