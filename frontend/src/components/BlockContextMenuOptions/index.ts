import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import type { ContextMenuOption } from "@/types/blockContextMenu";
import getBlockTemplate from "@/utils/blockTemplate";
import { createRegistry } from "@/utils/createRegistry";
import { promptCreateComponent } from "@/utils/dialogs";
import { confirm, detachBlockFromComponent, getBlockCopy, triggerCopyEvent } from "@/utils/helpers";
import { useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { nextTick, type Ref } from "vue";
import { __ } from "@/translation";

export const blockContextMenuOptions = createRegistry<ContextMenuOption>();

const copiedStyle = useStorage("copiedStyle", { blockId: "", style: {} }, sessionStorage) as Ref<StyleCopy>;

// the route chunk imports this after pinia is installed, so the lookups resolve
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const componentStore = useComponentStore();

const readOnly = () => builderStore.readOnlyMode;

const options: ContextMenuOption[] = [
	{
		name: "edit-html",
		label: __("Edit HTML"),
		action: ({ block }) => canvasStore.editHTML(block),
		condition: ({ block }) => block.isHTML(),
	},
	{
		name: "copy",
		label: __("Copy"),
		action: () => triggerCopyEvent(),
	},
	{
		name: "copy-style",
		label: __("Copy Style"),
		action: ({ block }) => {
			copiedStyle.value = { blockId: block.blockId, style: block.getStylesCopy() };
		},
	},
	{
		name: "paste-style",
		label: __("Paste Style"),
		action: ({ block }) => block.updateStyles(copiedStyle.value?.style as BlockStyleObjects),
		condition: ({ block }) =>
			Boolean(copiedStyle.value.blockId && copiedStyle.value?.blockId !== block.blockId),
		disabled: readOnly,
	},
	{
		name: "duplicate",
		label: __("Duplicate"),
		action: ({ block }) => block.duplicateBlock(),
		disabled: readOnly,
	},
	{
		name: "convert-to-collection",
		label: __("Convert To Collection"),
		action: ({ block }) => {
			block.isRepeaterBlock = true;
			toast.warning(__("Please select a collection"));
		},
		condition: ({ block }) =>
			block.isContainer() &&
			!block.isRoot() &&
			!block.isRepeater() &&
			!block.isChildOfComponentBlock() &&
			!block.isExtendedFromComponent(),
		disabled: readOnly,
	},
	{
		name: "remove-collection",
		label: __("Remove Collection"),
		action: ({ block }) => {
			block.isRepeaterBlock = false;
			block.dataKey = {};
		},
		condition: ({ block }) => block.isRepeater(),
		disabled: readOnly,
	},
	{
		name: "wrap-in-container",
		label: __("Wrap In Container"),
		action: ({ block }) => {
			const newBlockObj = getBlockTemplate("fit-container");
			const parentBlock = block.getParentBlock();
			if (!parentBlock) return;

			const selectedBlocks = canvasStore.activeCanvas?.selectedBlocks || [];
			const blockPosition = Math.min(...selectedBlocks.map(parentBlock.getChildIndex.bind(parentBlock)));
			const newBlock = parentBlock?.addChild(newBlockObj, blockPosition);

			let width = null as string | null;
			// move selected blocks to newBlock
			selectedBlocks
				.sort((a: Block, b: Block) => parentBlock.getChildIndex(a) - parentBlock.getChildIndex(b))
				.forEach((selectedBlock: Block) => {
					parentBlock?.removeChild(selectedBlock);
					newBlock?.addChild(selectedBlock);
					if (!width) {
						const blockWidth = selectedBlock.getStyle("width") as string | undefined;
						if (blockWidth && (blockWidth == "auto" || blockWidth.endsWith("%"))) {
							width = "100%";
						}
					}
				});

			if (width) {
				newBlock?.setStyle("width", width);
			}

			nextTick(() => {
				if (newBlock) {
					newBlock.selectBlock();
				}
			});
		},
		condition: ({ block }) => {
			if (block.isRoot()) return false;
			if (canvasStore.activeCanvas?.selectedBlocks.length === 1) return true;
			// check if all selected blocks are siblings
			const parentBlock = block.getParentBlock();
			if (!parentBlock) return false;
			const selectedBlocks = canvasStore.activeCanvas?.selectedBlocks || [];
			return selectedBlocks.every((selectedBlock: Block) => selectedBlock.getParentBlock() === parentBlock);
		},
		disabled: readOnly,
	},
	{
		name: "repeat-block",
		label: __("Repeat Block"),
		action: ({ block }) => {
			const repeaterBlockObj = getBlockTemplate("repeater");
			const parentBlock = block.getParentBlock();
			if (!parentBlock) return;
			const repeaterBlock = parentBlock.addChild(repeaterBlockObj, parentBlock.getChildIndex(block));
			repeaterBlock.addChild(getBlockCopy(block));
			parentBlock.removeChild(block);
			repeaterBlock.selectBlock();
			toast.warning(__("Please select a collection"));
		},
		condition: ({ block }) => !block.isRoot() && !block.isRepeater() && !block.isChildOfComponentBlock(),
		disabled: readOnly,
	},
	{
		name: "reset-overrides",
		label: __("Reset Overrides"),
		action: ({ block }) => block.resetOverrides(canvasStore.activeCanvas?.activeBreakpoint || "desktop"),
		condition: () => canvasStore.activeCanvas?.activeBreakpoint !== "desktop",
		disabled: ({ block }) =>
			builderStore.readOnlyMode ||
			!block?.hasOverrides(canvasStore.activeCanvas?.activeBreakpoint || "desktop"),
	},
	{
		name: "reset-changes",
		label: __("Reset Changes"),
		action: ({ block }) => {
			if (block.hasChildren()) {
				confirm(__("Reset changes in child blocks as well?")).then((confirmed) => {
					block.resetChanges(confirmed);
				});
			} else {
				block.resetChanges();
			}
		},
		condition: ({ block }) => block.isExtendedFromComponent(),
		disabled: readOnly,
	},
	{
		name: "sync-component",
		label: __("Sync Component"),
		action: ({ block }) => block.syncWithComponent(),
		condition: ({ block }) => Boolean(block.extendedFromComponent),
		disabled: readOnly,
	},
	{
		name: "reset-component",
		label: __("Reset Component"),
		action: ({ block }) => {
			confirm(__("Are you sure you want to reset?")).then((confirmed) => {
				if (confirmed) {
					block.resetWithComponent();
				}
			});
		},
		condition: ({ block }) => Boolean(block.extendedFromComponent),
		disabled: readOnly,
	},
	{
		name: "update-component",
		label: __("Update to Latest Component"),
		action: ({ block }) => componentStore.updatePinnedComponent(block),
		condition: ({ block }) =>
			componentStore.isPinOutdated(block.extendedFromComponent, block.componentVersion),
		disabled: readOnly,
	},
	{
		name: "edit-component",
		label: __("Edit Component"),
		action: ({ block }) => componentStore.editComponent(block),
		condition: ({ block }) => block.isExtendedFromComponent(),
		disabled: readOnly,
	},
	{
		name: "save-block-template",
		label: __("Save as Block Template"),
		action: () => {
			builderStore.showBlockTemplateDialog = true;
		},
		condition: ({ block }) => !block.isExtendedFromComponent() && Boolean(window.is_developer_mode),
		disabled: readOnly,
	},
	{
		name: "save-component",
		label: __("Save As Component"),
		action: ({ block }) => promptCreateComponent(block),
		condition: ({ block }) => !block.isExtendedFromComponent(),
		disabled: readOnly,
	},
	{
		name: "detach-component",
		label: __("Detach Component"),
		action: ({ block }) => {
			const newBlock = detachBlockFromComponent(block, null);
			if (newBlock) {
				newBlock.selectBlock();
			}
			block.getParentBlock()?.replaceChild(block, newBlock);
		},
		condition: ({ block }) => Boolean(block.extendedFromComponent),
		disabled: readOnly,
	},
	{
		name: "rename",
		label: __("Rename"),
		action: ({ target }) => {
			const layerLabel = target?.closest("[data-block-layer-id]")?.querySelector(".layer-label");
			if (!layerLabel) return;
			layerLabel.dispatchEvent(new Event("dblclick"));
			nextTick(() => {
				// selct all text in the layerLabel
				const range = document.createRange();
				range.selectNodeContents(layerLabel);
				const selection = window.getSelection();
				if (selection) {
					selection.removeAllRanges();
					selection.addRange(range);
				}
			});
		},
		condition: ({ block, fromLayersPanel }) =>
			!block.isRoot() && !block.isChildOfComponentBlock() && fromLayersPanel,
		disabled: readOnly,
	},
	{
		name: "delete",
		label: __("Delete"),
		action: () => {
			const selectedBlocks = canvasStore.activeCanvas?.selectedBlocks || [];
			selectedBlocks.forEach((selectedBlock: Block) => {
				canvasStore.activeCanvas?.removeBlock(selectedBlock);
			});
		},
		condition: ({ block }) =>
			!block.isRoot() &&
			!block.isChildOfComponentBlock() &&
			block.isVisible() &&
			Boolean(block.getParentBlock()),
		disabled: readOnly,
	},
];

options.forEach(blockContextMenuOptions.register);
