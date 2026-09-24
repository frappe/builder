import type Block from "@/block";
import builderProjectFolder from "@/data/builderProjectFolder";
import webComponent from "@/data/webComponent";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent } from "@/types/doctypes";
import { getBlockCopy, getBlockString } from "@/utils/helpers";
import { dialog } from "frappe-ui";
import { __ } from "@/translation";

// Imperative dialogs that replace single-purpose modal components. Each opens
// a frappe-ui prompt that auto-closes once `onConfirm` resolves; throwing from
// onConfirm surfaces the error inline and keeps the dialog open.

// dismissing resolves false, so a stray Esc never uploads
export function promptOversizedSVG(bytes: number): Promise<boolean> {
	return new Promise((resolve) => {
		dialog.confirm({
			title: __("Large SVG"),
			message: __(
				"This SVG is {0} KB. Kept inline it is stored in the page itself, which makes saving and editing slower. Upload it as a file instead?",
				[String(Math.round(bytes / 1024))],
			),
			confirmLabel: __("Upload as File"),
			cancelLabel: __("Keep Inline"),
			onConfirm: () => resolve(true),
			onCancel: () => resolve(false),
		});
	});
}

export function promptCreateFolder() {
	dialog.prompt({
		title: __("Create New Folder"),
		size: "sm",
		confirmLabel: __("Create Folder"),
		fields: [{ name: "folder_name", label: __("Folder Name"), required: true }],
		onConfirm: async ({ values }) => {
			await builderProjectFolder.insert.submit({ folder_name: values.folder_name });
		},
	});
}

export function promptCreateComponent(block: Block) {
	const componentStore = useComponentStore();
	const canvasStore = useCanvasStore();
	const pageStore = usePageStore();
	dialog.prompt({
		title: __("New Component"),
		size: "sm",
		confirmLabel: __("Save"),
		fields: [
			{
				name: "componentName",
				label: __("Component Name"),
				required: true,
				defaultValue: block.blockName || "",
			},
			{ name: "isGlobalComponent", type: "checkbox", label: __("Global Component") },
		],
		onConfirm: async ({ values }) => {
			const blockCopy = getBlockCopy(block, true);
			blockCopy.removeStyle("left");
			blockCopy.removeStyle("top");
			blockCopy.removeStyle("position");
			const componentData = (await webComponent.insert.submit({
				block: getBlockString(blockCopy),
				component_name: values.componentName,
				for_web_page: values.isGlobalComponent ? null : pageStore.selectedPage,
			})) as BuilderComponent;
			componentStore.setComponentMap(componentData);
			const updatedBlock = canvasStore.activeCanvas?.findBlock(block.blockId);
			updatedBlock?.extendFromComponent(componentData.name);
			if (updatedBlock) {
				await componentStore.pinComponentInstance(updatedBlock, componentData.name);
				pageStore.savePage();
			}
		},
	});
}
