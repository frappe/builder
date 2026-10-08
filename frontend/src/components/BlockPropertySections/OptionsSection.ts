import InlineInput from "@/components/Controls/InlineInput.vue";
import VisibilityInput from "@/components/VisibilityInput.vue";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};

const setID = (val: string) => {
	// a space would split the id, so #section links could never match it
	const id = val.trim().replace(/\s+/g, "-");
	blockController.getFirstSelectedBlock()?.setId(id || undefined);
};

const optionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: __("Class"),
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
				label: __("ID"),
				description: __("Links to #id scroll to this block"),
				modelValue: blockController.getFirstSelectedBlock()?.getId(),
			};
		},
		searchKeyWords: "ID, Anchor, Section, Element ID, Scroll To",
		events: {
			"update:modelValue": (val: string) => setID(val || ""),
		},
		condition: () => !blockController.multipleBlocksSelected(),
	},
	{
		component: VisibilityInput,
		getProps: () => {
			return {
				label: __("Condition"),
				property: "visibilityCondition",
				getModelValue: () =>
					(blockController.getKeyValue("visibilityCondition") as BlockVisibilityCondition).key,
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
	name: __("Options"),
	properties: optionsSectionProperties,
};
