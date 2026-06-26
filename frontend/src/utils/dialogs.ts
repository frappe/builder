import type Block from "@/block";
import { useDashboardState } from "@/composables/useDashboardState";
import builderProjectFolder from "@/data/builderProjectFolder";
import webComponent from "@/data/webComponent";
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderComponent, BuilderPage, BuilderProjectFolder } from "@/types/doctypes";
import { getBlockCopy, getBlockString } from "@/utils/helpers";
import { createResource, dialog } from "frappe-ui";

// Imperative dialogs that replace single-purpose modal components. Each opens
// a frappe-ui prompt that auto-closes once `onConfirm` resolves; throwing from
// onConfirm surfaces the error inline and keeps the dialog open.

export function promptCreateFolder() {
	dialog.prompt({
		title: "Create New Folder",
		size: "sm",
		confirmLabel: "Create Folder",
		fields: [{ name: "folder_name", label: "Folder Name", required: true }],
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
		title: "New Component",
		size: "sm",
		confirmLabel: "Save",
		fields: [
			{
				name: "componentName",
				label: "Component Name",
				required: true,
				defaultValue: block.blockName || "",
			},
			{ name: "isGlobalComponent", type: "checkbox", label: "Global Component" },
			{ name: "componentCategory", label: "Category" },
			{ name: "componentPreview", label: "Preview Image" },
			{ name: "componentPreviewWidth", type: "number", label: "Preview Width", defaultValue: 1 },
			{ name: "componentPreviewHeight", type: "number", label: "Preview Height", defaultValue: 1 },
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
				category: values.componentCategory,
				preview: values.componentPreview,
				preview_width: getPreviewSize(values.componentPreviewWidth),
				preview_height: getPreviewSize(values.componentPreviewHeight),
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

function getPreviewSize(value: string | number) {
	const size = Number(value) || 1;
	return Math.min(Math.max(size, 1), 2);
}

export function promptSelectFolder() {
	const { selectedPages, selectionMode } = useDashboardState();
	const builderStore = useBuilderStore();
	const options = [
		{ label: "Home", value: "" },
		...(builderProjectFolder.data || []).map((p: BuilderProjectFolder) => ({
			label: p.folder_name,
			value: p.folder_name,
		})),
	];
	dialog.prompt({
		title: "Select Folder",
		size: "sm",
		fields: [
			{
				name: "folder",
				type: "select",
				label: "Folder",
				defaultValue: builderStore.activeFolder || "",
				options,
			},
		],
		onConfirm: async ({ values }) => {
			const folder = values.folder;
			if (folder === builderStore.activeFolder) return;
			await createResource({
				method: "POST",
				url: "builder.api.update_page_folder",
			}).submit({
				pages: Array.from(selectedPages.value),
				folder_name: folder,
			});
			for (const pageName of selectedPages.value) {
				const page = webPages.data?.find((p: BuilderPage) => p.name === pageName);
				if (page) page.project_folder = folder;
			}
			selectedPages.value.clear();
			selectionMode.value = false;
			builderStore.activeFolder = folder;
		},
	});
}
