import { computed } from "vue";
import CodeEditor from "../Controls/CodeEditor.vue";
import blockController from "@/utils/blockController";

const blockScriptProperties = [
	{
		component: CodeEditor,
		getProps: () => {
			return {
				modelValue: blockController.getBlockScript(),
				type: "JavaScript",
				readonly: false,
				height: "200px",
				showLineNumbers: true,
				autofocus: true,
				showSaveButton: true,
				description:
					"Add custom scripts to enhance block functionality.",
			};
		},
		searchKeyWords: "Block Script, Script, JS, JavaScript, Custom Script",
		events: {
			save: (script: string) => blockController.setBlockScript(script),
		},
	},
];

export default {
	name: "Block Script",
	properties: blockScriptProperties,
	collapsed: !blockController.getBlockScript()?.trim(),
	condition: () => !blockController.multipleBlocksSelected(),
};
