import InlineInput from "@/components/Controls/InlineInput.vue";
import VisibilityInput from "@/components/VisibilityInput.vue";
import blockController from "@/utils/blockController";

const setClasses = (val: string) => {
	const classes = val.split(",").map((c) => c.trim());
	blockController.setClasses(classes);
};

const optionsSectionProperties = [
	{
		component: InlineInput,
		getProps: () => {
			return {
				label: "类",
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
				label: "条件",
				property: "visibilityCondition",
				getModelValue: () => (blockController.getKeyValue("visibilityCondition") as BlockVisibilityCondition).key,
				setModelValue: (val: BlockVisibilityCondition) => {
					blockController.setKeyValue("visibilityCondition", val);
				},
				description:
					"根据条件显示/隐藏该区块的可见性条件。传入在「数据脚本」中创建的布尔变量。<br><b>注意：</b> 该条件仅在预览模式下生效。",
			};
		},
		searchKeyWords:
			"Condition, Visibility, VisibilityCondition, Visibility Condition, show, hide, display, hideIf, showIf",
		condition: () => !blockController.isRoot(),
	},
];

export default {
	name: "选项",
	properties: optionsSectionProperties,
};
