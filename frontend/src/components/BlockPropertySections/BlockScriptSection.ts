import { computed } from "vue";
import CodeEditor from "../Controls/CodeEditor.vue";
import blockController from "@/utils/blockController";
import useCanvasStore from "@/stores/canvasStore";
import GenericControl from "../Controls/GenericControl.vue";

const blockScriptProperties = [
	{
		component: GenericControl,
		getProps: () => {
			return {
				component: CodeEditor,
				type: "JavaScript",
				label: "Block Client Script",
				autofocus: false,
				height: "60px",
				controlType: "key",
				labelPlacement: "top",
				getModelValue: () => blockController.getBlockClientScript() || "",
				setModelValue: (val: string) => blockController.setBlockClientScript(val),
				actionButton: {
					label: "Expand",
					icon: "maximize-2",
					handler: () => {
						useCanvasStore().editBlockClientScript(blockController.getSelectedBlocks()[0]);
					},
				},
			};
		},
		searchKeyWords: "Block Client Script, Client Script, JS, JavaScript, Custom Script"
	},
	{
		component: GenericControl,
		getProps: () => {
			return {
				component: CodeEditor,
				type: "Python",
				label: "Block Data Script",
				autofocus: false,
				height: "60px",
				controlType: "key",
				labelPlacement: "top",
				getModelValue: () => blockController.getBlockDataScript() || "",
				setModelValue: (val: string) => blockController.setBlockDataScript(val),
				actionButton: {
					label: "Expand",
					icon: "maximize-2",
					handler: () => {
						useCanvasStore().editBlockDataScript(blockController.getSelectedBlocks()[0]);
					},
				},
			};
		},
		searchKeyWords: "Block Data Script, Data Script, Python, Py, Custom Script",
	},
];

export default {
	name: "Block Script",
	properties: blockScriptProperties,
	collapsed: false,
	condition: () => !blockController.multipleBlocksSelected(),
};
