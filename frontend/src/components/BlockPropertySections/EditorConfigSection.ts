import BasePropertyControl from "@/components/Controls/BasePropertyControl.vue";
import InlineInput from "@/components/Controls/InlineInput.vue";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import { __ } from "@/translation";

const getEditorConfig = (): BlockEditorConfig => {
	return blockController.getFirstSelectedBlock()?.editorConfig || {};
};

const setEditorConfig = (patch: Partial<BlockEditorConfig>) => {
	const block = blockController.getFirstSelectedBlock();
	if (!block) return;
	block.editorConfig = { ...block.editorConfig, ...patch };
};

const editorConfigSectionProperties = [
	{
		component: InlineInput,
		getProps: () => ({
			label: __("Layer Icon"),
			modelValue: getEditorConfig().icon || "",
			placeholder: "e.g. play-circle",
		}),
		events: {
			"update:modelValue": (val: string) => setEditorConfig({ icon: val || undefined }),
		},
		searchKeyWords: "Editor, Config, Icon, Layer Icon, EditorConfig",
	},
	{
		component: BasePropertyControl,
		getProps: () => ({
			propertyKey: "showChildrenInEditor",
			label: __("Show Children"),
			component: OptionToggle,
			enableStates: false,
			options: [
				{ label: __("Show"), value: true },
				{ label: __("Hide"), value: false },
			],
			getModelValue: () => {
				const val = getEditorConfig().showChildrenInEditor;
				return val === false ? false : true;
			},
			setModelValue: (val: boolean) => setEditorConfig({ showChildrenInEditor: val }),
		}),
		searchKeyWords: "Editor, Config, Show Children, showChildrenInEditor, Layers, EditorConfig",
	},
];

export default {
	name: __("Editor Config"),
	properties: editorConfigSectionProperties,
	collapsed: true,
	condition: () => {
		const canvasStore = useCanvasStore();
		return (
			!blockController.multipleBlocksSelected() &&
			canvasStore.editingMode === "fragment" &&
			window.is_developer_mode
		);
	},
};
