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
import { useDateFormat, useStorage } from "@vueuse/core";
import { createResource, dialog, toast } from "frappe-ui";
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

function choose<T>(resolve: (choice: T) => void, choice: T) {
	return ({ close }: { close: () => void }) => {
		resolve(choice);
		close();
	};
}

// dismissing resolves null, so a stray Esc never saves
export function promptSharedScriptSave(scriptName: string, otherPages: string): Promise<"all" | "copy" | null> {
	return new Promise((resolve) => {
		dialog.confirm({
			title: __("Update a shared script?"),
			message:
				otherPages === "1"
					? __("{0} is also used on 1 other page. Saving changes how that page behaves too.", [scriptName])
					: __("{0} is also used on {1} other pages. Saving changes how those pages behave too.", [
							scriptName,
							otherPages,
						]),
			icon: "lucide-alert-circle",
			theme: "amber",
			actions: [
				{ label: __("Save as Copy for This Page"), variant: "subtle", onClick: choose(resolve, "copy") },
				{ label: __("Update All Pages"), variant: "solid", onClick: choose(resolve, "all") },
			],
			onCancel: () => resolve(null),
		});
	});
}

// dismissing resolves false, so a stray Esc keeps the edit
export function promptDiscardScriptEdits(scriptName: string): Promise<boolean> {
	return new Promise((resolve) => {
		dialog.confirm({
			title: __("Discard unsaved changes?"),
			message: __("Your edits to {0} have not been saved.", [scriptName]),
			theme: "red",
			confirmLabel: __("Discard"),
			cancelLabel: __("Keep Editing"),
			onConfirm: () => resolve(true),
			onCancel: () => resolve(false),
		});
	});
}

// dismissing resolves null and leaves the edit in the editor, unsaved
export function promptScriptConflict(scriptName: string): Promise<"overwrite" | "reload" | null> {
	return new Promise((resolve) => {
		dialog.confirm({
			title: __("Script changed elsewhere"),
			message: __(
				"{0} was saved somewhere else (another tab or another person) after you opened it. Overwrite that version with yours, or load it and drop your edit?",
				[scriptName],
			),
			icon: "lucide-alert-circle",
			theme: "amber",
			actions: [
				{ label: __("Load Latest"), variant: "subtle", onClick: choose(resolve, "reload") },
				{ label: __("Overwrite"), variant: "solid", theme: "red", onClick: choose(resolve, "overwrite") },
			],
			onCancel: () => resolve(null),
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

export function promptSelectFolder() {
	const { selectedPages, selectionMode } = useDashboardState();
	const builderStore = useBuilderStore();
	const options = [
		{ label: __("Home"), value: "" },
		...(builderProjectFolder.data || []).map((p: BuilderProjectFolder) => ({
			label: p.folder_name as string,
			value: p.folder_name as string,
		})),
	];
	dialog.prompt({
		title: __("Select Folder"),
		size: "sm",
		fields: [
			{
				name: "folder",
				type: "select",
				label: __("Folder"),
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

export function promptRenamePage(page: BuilderPage) {
	dialog.prompt({
		title: __("Rename Page"),
		size: "sm",
		confirmLabel: __("Rename"),
		fields: [{ name: "page_title", label: __("Page Title"), required: true, defaultValue: page.page_title || "" }],
		onConfirm: async ({ values }) => {
			const pageTitle = values.page_title.trim();
			if (!pageTitle || pageTitle === page.page_title) return;
			await webPages.setValue.submit({ name: page.name, page_title: pageTitle });
			page.page_title = pageTitle;
		},
	});
}

const hideSaveVersionPrompt = useStorage("hideSaveVersionPrompt", false);

async function saveVersionIfChanged(pageName: string, label?: string) {
	const pageStore = usePageStore();
	await pageStore.waitTillPageIsSaved();
	if (pageStore.selectedPage !== pageName) throw new Error("Page changed while saving");
	const res = await pageStore.createManualSnapshot(label, pageName);
	return Boolean(res?.message);
}

export function saveVersion(label?: string) {
	const saving = saveVersionIfChanged(usePageStore().selectedPage as string, label);
	toast.promise(saving, {
		loading: __("Saving version..."),
		success: (isSaved: boolean) => (isSaved ? __("Version saved") : __("No changes since the last version")),
		error: () => __("Could not save version"),
	});
	return saving;
}

export function quickSaveVersion() {
	return saveVersion(useDateFormat(new Date(), "YYYY-MM-DD HH:mm:ss").value);
}

// Mod+S: changes autosave, so the shortcut offers to save a version instead
export function promptSaveVersion() {
	if (hideSaveVersionPrompt.value) return quickSaveVersion();
	dialog.prompt({
		title: __("Save a Version History"),
		message: __("Changes are saved automatically. This action saves the current state as a version."),
		size: "sm",
		confirmLabel: __("Save Version"),
		fields: [{ name: "dontRemind", type: "checkbox", label: __("Don't remind me again") }],
		onConfirm: async ({ values }) => {
			hideSaveVersionPrompt.value = Boolean(values.dontRemind);
			quickSaveVersion();
		},
	});
}
