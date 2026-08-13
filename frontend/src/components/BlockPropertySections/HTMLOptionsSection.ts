import CodeEditor from "@/components/Controls/CodeEditor.vue";
import blockController from "@/utils/blockController";
import useCanvasStore from "../../stores/canvasStore";
import BasePropertyControl from "../Controls/BasePropertyControl.vue";
import { __ } from "@/translation";

const HTMLOptionsSectionProperties = [
	{
		component: BasePropertyControl,
		getProps: () => {
			return {
				component: CodeEditor,
				type: "HTML",
				label: __("HTML"),
				autofocus: false,
				height: "60px",
				controlType: "key",
				propertyKey: "innerHTML",
				labelPlacement: "top",
				getModelValue: () => blockController.getInnerHTML() || "",
				setModelValue: (val: string) => blockController.setInnerHTML(val),
				allowDynamicValue: true,
				actionButton: {
					label: __("Expand"),
					icon: "lucide-maximize-2",
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
	name: __("HTML Options"),
	properties: HTMLOptionsSectionProperties,
	condition: () => blockController.isHTML() || (blockController.getInnerHTML() && !blockController.isText()),
};
