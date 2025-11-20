import { computed } from "vue";
import CodeEditor from "../Controls/CodeEditor.vue";
import blockController from "@/utils/blockController";
import useCanvasStore from "@/stores/canvasStore";

const blockScriptProperties = [
	{
		component: CodeEditor,
		getProps: () => {
			return {
				modelValue: blockController.getBlockScript(),
				getModelValue: () => blockController.getBlockScript() || "",
				type: "JavaScript",
				readonly: false,
				height: "200px",
				showLineNumbers: true,
				autofocus: true,
				actionButton: {
					label: "Expand",
					icon: "maximize-2",
					handler: () => {
						useCanvasStore().editBlockScript(blockController.getSelectedBlocks()[0]);
					},
				},
			};
		},
		searchKeyWords: "Block Script, Script, JS, JavaScript, Custom Script",
		events: {
			save: (script: string) => blockController.setBlockScript(script),
			"update:modelValue": (script: string) => blockController.setBlockScript(script),
		},
	},
];

export default {
	name: "Block Script",
	properties: blockScriptProperties,
	collapsed: false,
	condition: () => !blockController.multipleBlocksSelected(),
};
