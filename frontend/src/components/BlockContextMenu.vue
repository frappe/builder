<template>
	<div>
		<ContextMenu ref="contextMenu" :options="contextMenuOptions" :context="menuContext" />
		<NewBlockTemplate
			v-if="menuContext"
			:block="menuContext.block"
			v-model="builderStore.showBlockTemplateDialog"></NewBlockTemplate>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import ContextMenu from "@/components/ContextMenu.vue";
import NewBlockTemplate from "@/components/Modals/NewBlockTemplate.vue";
import type { BlockMenuContext, ContextMenuOption } from "@/types/blockContextMenu";
import { promptCreateComponent } from "@/utils/dialogs";
import useAIStore from "@/stores/aiStore";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import getBlockTemplate from "@/utils/blockTemplate";
import { confirm, detachBlockFromComponent, getBlockCopy, triggerCopyEvent } from "@/utils/helpers";
import { useStorage } from "@vueuse/core";
import { Ref, nextTick, ref } from "vue";
import { toast } from "frappe-ui";

const builderStore = useBuilderStore();
const componentStore = useComponentStore();
const canvasStore = useCanvasStore();
const aiStore = useAIStore();

const contextMenu = ref(null) as unknown as Ref<InstanceType<typeof ContextMenu>>;
const menuContext = ref(null) as unknown as Ref<BlockMenuContext>;

const showContextMenu = (event: MouseEvent, refBlock: Block) => {
	const target = event.target as HTMLElement;
	menuContext.value = {
		block: refBlock,
		target,
		fromLayersPanel: Boolean(target.closest(".block-layers")),
	};
	if (refBlock.isRoot()) return;
	contextMenu.value?.show(event);
};

const copiedStyle = useStorage("copiedStyle", { blockId: "", style: {} }, sessionStorage) as Ref<StyleCopy>;

const contextMenuOptions: ContextMenuOption[] = [
	{
		name: "edit-with-ai",
		label: "Edit with AI",
		rank: 10,
		action: ({ block }) => aiStore.editWithAI(block),
		condition: ({ block }) => builderStore.isAIEnabled && !block.isRoot(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "rewrite-ai",
		label: "Rewrite (AI)",
		rank: 20,
		action: ({ block }) => aiStore.runDirectAI(block, "rewrite_text", "Rewrite the content"),
		condition: ({ block }) => builderStore.isAIEnabled && block.isText() && !block.isRoot(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "replace-image-ai",
		label: "Replace Image (AI)",
		rank: 30,
		action: ({ block }) => aiStore.runDirectAI(block, "replace_image", "Replace image"),
		condition: ({ block }) => builderStore.isAIEnabled && block.isImage() && !block.isRoot(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "edit-html",
		label: "Edit HTML",
		rank: 40,
		action: ({ block }) => canvasStore.editHTML(block),
		condition: ({ block }) => block.isHTML(),
	},
	{
		name: "copy",
		label: "Copy",
		rank: 50,
		action: () => triggerCopyEvent(),
	},
	{
		name: "copy-style",
		label: "Copy Style",
		rank: 60,
		action: ({ block }) => {
			copiedStyle.value = { blockId: block.blockId, style: block.getStylesCopy() };
		},
	},
	{
		name: "paste-style",
		label: "Paste Style",
		rank: 70,
		action: ({ block }) => block.updateStyles(copiedStyle.value?.style as BlockStyleObjects),
		condition: ({ block }) =>
			Boolean(copiedStyle.value.blockId && copiedStyle.value?.blockId !== block.blockId),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "duplicate",
		label: "Duplicate",
		rank: 80,
		action: ({ block }) => block.duplicateBlock(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "convert-to-collection",
		label: "Convert To Collection",
		rank: 90,
		action: ({ block }) => {
			block.isRepeaterBlock = true;
			toast.warning("Please select a collection");
		},
		condition: ({ block }) =>
			block.isContainer() &&
			!block.isRoot() &&
			!block.isRepeater() &&
			!block.isChildOfComponentBlock() &&
			!block.isExtendedFromComponent(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "remove-collection",
		label: "Remove Collection",
		rank: 100,
		action: ({ block }) => {
			block.isRepeaterBlock = false;
			block.dataKey = {};
		},
		condition: ({ block }) => block.isRepeater(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "wrap-in-container",
		label: "Wrap In Container",
		rank: 110,
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
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "repeat-block",
		label: "Repeat Block",
		rank: 120,
		action: ({ block }) => {
			const repeaterBlockObj = getBlockTemplate("repeater");
			const parentBlock = block.getParentBlock();
			if (!parentBlock) return;
			const repeaterBlock = parentBlock.addChild(repeaterBlockObj, parentBlock.getChildIndex(block));
			repeaterBlock.addChild(getBlockCopy(block));
			parentBlock.removeChild(block);
			repeaterBlock.selectBlock();
			toast.warning("Please select a collection");
		},
		condition: ({ block }) => !block.isRoot() && !block.isRepeater() && !block.isChildOfComponentBlock(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "reset-overrides",
		label: "Reset Overrides",
		rank: 130,
		action: ({ block }) => block.resetOverrides(canvasStore.activeCanvas?.activeBreakpoint || "desktop"),
		condition: () => canvasStore.activeCanvas?.activeBreakpoint !== "desktop",
		disabled: ({ block }) =>
			builderStore.readOnlyMode ||
			!block?.hasOverrides(canvasStore.activeCanvas?.activeBreakpoint || "desktop"),
	},
	{
		name: "reset-changes",
		label: "Reset Changes",
		rank: 140,
		action: ({ block }) => {
			if (block.hasChildren()) {
				confirm("Reset changes in child blocks as well?").then((confirmed) => {
					block.resetChanges(confirmed);
				});
			} else {
				block.resetChanges();
			}
		},
		condition: ({ block }) => block.isExtendedFromComponent(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "sync-component",
		label: "Sync Component",
		rank: 150,
		action: ({ block }) => block.syncWithComponent(),
		condition: ({ block }) => Boolean(block.extendedFromComponent),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "reset-component",
		label: "Reset Component",
		rank: 160,
		action: ({ block }) => {
			confirm("Are you sure you want to reset?").then((confirmed) => {
				if (confirmed) {
					block.resetWithComponent();
				}
			});
		},
		condition: ({ block }) => Boolean(block.extendedFromComponent),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "update-component",
		label: "Update to Latest Component",
		rank: 170,
		action: ({ block }) => componentStore.updatePinnedComponent(block),
		condition: ({ block }) =>
			componentStore.isPinOutdated(block.extendedFromComponent, block.componentVersion),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "edit-component",
		label: "Edit Component",
		rank: 180,
		action: ({ block }) => componentStore.editComponent(block),
		condition: ({ block }) => block.isExtendedFromComponent(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "save-block-template",
		label: "Save as Block Template",
		rank: 190,
		action: () => {
			builderStore.showBlockTemplateDialog = true;
		},
		condition: ({ block }) => !block.isExtendedFromComponent() && Boolean(window.is_developer_mode),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "save-component",
		label: "Save As Component",
		rank: 200,
		action: ({ block }) => promptCreateComponent(block),
		condition: ({ block }) => !block.isExtendedFromComponent(),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "detach-component",
		label: "Detach Component",
		rank: 210,
		action: ({ block }) => {
			const newBlock = detachBlockFromComponent(block, null);
			if (newBlock) {
				newBlock.selectBlock();
			}
			block.getParentBlock()?.replaceChild(block, newBlock);
		},
		condition: ({ block }) => Boolean(block.extendedFromComponent),
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "rename",
		label: "Rename",
		rank: 220,
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
		disabled: () => builderStore.readOnlyMode,
	},
	{
		name: "delete",
		label: "Delete",
		rank: 230,
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
		disabled: () => builderStore.readOnlyMode,
	},
];

defineExpose({
	showContextMenu,
});
</script>
