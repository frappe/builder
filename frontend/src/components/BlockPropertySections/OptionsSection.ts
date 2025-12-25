import InlineInput from "@/components/Controls/InlineInput.vue";
import blockController from "@/utils/blockController";
import VisibilityInput from "@/components/VisibilityInput.vue";

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
		component: VisibilityInput,
		getProps: () => {
			return {
				label: "Condition",
				getModelValue: () => (blockController.getKeyValue("visibilityCondition") as BlockVisibilityCondition).key,
				setModelValue: (val: BlockVisibilityCondition) => {
					blockController.setKeyValue("visibilityCondition", val);
				},
				description:
					"Visibility condition to show/hide the block based on a condition. Pass a boolean variable created in your Data Script.<br><b>Note:</b> This is only evaluated in the preview mode.",
			};
		},
		searchKeyWords:
			"Condition, Visibility, VisibilityCondition, Visibility Condition, show, hide, display, hideIf, showIf",
		condition: () => !blockController.isRoot(),
	},
];

export default {
	name: "Options",
	properties: optionsSectionProperties,
};
