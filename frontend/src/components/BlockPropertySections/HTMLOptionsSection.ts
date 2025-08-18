import CodeEditor from "@/components/Controls/CodeEditor.vue";
import blockController from "@/utils/blockController";
import useCanvasStore from "../../stores/canvasStore";
import PropertyControl from "../Controls/PropertyControl.vue";

const HTMLOptionsSectionProperties = [
	{
		component: PropertyControl,
		getProps: () => {
			return {
				component: CodeEditor,
				type: "HTML",
				label: "HTML",
				autofocus: false,
				height: "60px",
				controlType: "key",
				styleProperty: "innerHTML",
				labelPlacement: "top",
				getModelValue: () => blockController.getInnerHTML() || "",
				setModelValue: (val: string) => blockController.setInnerHTML(val),
				allowDynamicValue: true,
				actionButton: {
					label: "Expand",
					icon: "maximize-2",
					handler: () => {
						useCanvasStore().editHTML(blockController.getSelectedBlocks()[0]);
					},
				},
			};
		},
		searchKeyWords: "HTML, InnerHTML, Inner HTML",
		condition: () =>
			blockController.isHTML() || (blockController.getInnerHTML() && !blockController.isText()),
	},
];

export default {
	name: "HTML Options",
	properties: HTMLOptionsSectionProperties,
	condition: () => blockController.isHTML() || (blockController.getInnerHTML() && !blockController.isText()),
};
