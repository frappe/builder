<template>
	<div>
		<ContextMenu
			v-if="contextMenuVisible"
			:pos-x="posX"
			:pos-y="posY"
			:options="contextMenuOptions"
			@select="handleContextMenuSelect"
			v-on-click-outside="() => (contextMenuVisible = false)" />
		<NewComponent v-if="block" :block="block" v-model="showNewComponentDialog"></NewComponent>
		<NewBlockTemplate v-if="block" :block="block" v-model="showBlockTemplateDialog"></NewBlockTemplate>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import ContextMenu from "@/components/ContextMenu.vue";
import NewBlockTemplate from "@/components/Modals/NewBlockTemplate.vue";
import NewComponent from "@/components/Modals/NewComponent.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import getBlockTemplate from "@/utils/blockTemplate";
import { confirm, detachBlockFromComponent, getBlockCopy, triggerCopyEvent } from "@/utils/helpers";
import { vOnClickOutside } from "@vueuse/components";
import { useStorage } from "@vueuse/core";
import { Ref, nextTick, ref } from "vue";
import { toast } from "vue-sonner";

const componentStore = useComponentStore();
const canvasStore = useCanvasStore();
const builderStore = useBuilderStore();

const contextMenuVisible = ref(false);
const posX = ref(0);
const posY = ref(0);
const triggeredFromLayersPanel = ref(false);

const block = ref(null) as unknown as Ref<Block>;

const showNewComponentDialog = ref(false);
const showBlockTemplateDialog = ref(false);
const target = ref(null) as unknown as Ref<HTMLElement>;

const showContextMenu = (event: MouseEvent, refBlock: Block) => {
	block.value = refBlock;
	// check if the event is triggered from layers panel
	target.value = event.target as HTMLElement;
	const layersPanel = target.value.closest(".block-layers");
	triggeredFromLayersPanel.value = Boolean(layersPanel);

	if (block.value.isRoot()) return;
	contextMenuVisible.value = true;
	posX.value = event.pageX;
	posY.value = event.pageY;
	event.preventDefault();
	event.stopPropagation();
};

const handleContextMenuSelect = (action: CallableFunction) => {
	action();
	contextMenuVisible.value = false;
};

const copiedStyle = useStorage("copiedStyle", { blockId: "", style: {} }, sessionStorage) as Ref<StyleCopy>;

const copyStyle = () => {
	copiedStyle.value = {
		blockId: block.value.blockId,
		style: block.value.getStylesCopy(),
	};
};

const pasteStyle = () => {
	block.value.updateStyles(copiedStyle.value?.style as BlockStyleObjects);
};

const duplicateBlock = () => {
	block.value.duplicateBlock();
};

const contextMenuOptions: ContextMenuOption[] = [
	{
		label: "Edit HTML",
		action: () => {
			canvasStore.editHTML(block.value);
		},
		condition: () => block.value.isHTML(),
	},
	{ label: "Copy", action: () => triggerCopyEvent() },
	{ label: "Copy Style", action: copyStyle },
	{
		label: "Paste Style",
		action: pasteStyle,
		condition: () => Boolean(copiedStyle.value.blockId && copiedStyle.value?.blockId !== block.value.blockId),
	},
	{ label: "Duplicate", action: duplicateBlock },
	{
		label: "Convert To Collection",
		action: () => {
			block.value.isRepeaterBlock = true;
			toast.warning("Please select a collection");
		},
		condition: () =>
			block.value.isContainer() &&
			!block.value.isRoot() &&
			!block.value.isRepeater() &&
			!block.value.isChildOfComponentBlock() &&
			!block.value.isExtendedFromComponent(),
	},
	{
		label: "Remove Collection",
		action: () => {
			block.value.isRepeaterBlock = false;
			block.value.dataKey = {};
		},
		condition: () => block.value.isRepeater(),
	},
	{
		label: "Wrap In Container",
		action: () => {
			const newBlockObj = getBlockTemplate("fit-container");
			const parentBlock = block.value.getParentBlock();
			if (!parentBlock) return;

			const selectedBlocks = canvasStore.activeCanvas?.selectedBlocks || [];
			const blockPosition = Math.min(...selectedBlocks.map(parentBlock.getChildIndex.bind(parentBlock)));
			const newBlock = parentBlock?.addChild(newBlockObj, blockPosition);

			let width = null as string | null;
			// move selected blocks to newBlock
			selectedBlocks
				.sort((a: Block, b: Block) => parentBlock.getChildIndex(a) - parentBlock.getChildIndex(b))
				.forEach((block: Block) => {
					parentBlock?.removeChild(block);
					newBlock?.addChild(block);
					if (!width) {
						const blockWidth = block.getStyle("width") as string | undefined;
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
		condition: () => {
			if (block.value.isRoot()) return false;
			if (canvasStore.activeCanvas?.selectedBlocks.length === 1) return true;
			// check if all selected blocks are siblings
			const parentBlock = block.value.getParentBlock();
			if (!parentBlock) return false;
			const selectedBlocks = canvasStore.activeCanvas?.selectedBlocks || [];
			return selectedBlocks.every((block: Block) => block.getParentBlock() === parentBlock);
		},
	},
	{
		label: "Repeat Block",
		action: () => {
			const repeaterBlockObj = getBlockTemplate("repeater");
			const parentBlock = block.value.getParentBlock();
			if (!parentBlock) return;
			const repeaterBlock = parentBlock.addChild(repeaterBlockObj, parentBlock.getChildIndex(block.value));
			repeaterBlock.addChild(getBlockCopy(block.value));
			parentBlock.removeChild(block.value);
			repeaterBlock.selectBlock();
			toast.warning("Please select a collection");
		},
		condition: () =>
			!block.value.isRoot() && !block.value.isRepeater() && !block.value.isChildOfComponentBlock(),
	},
	{
		label: "Reset Overrides",
		condition: () => canvasStore.activeCanvas?.activeBreakpoint !== "desktop",
		disabled: () => !block.value?.hasOverrides(canvasStore.activeCanvas?.activeBreakpoint || "desktop"),
		action: () => {
			block.value.resetOverrides(canvasStore.activeCanvas?.activeBreakpoint || "desktop");
		},
	},
	{
		label: "Reset Changes",
		action: () => {
			if (block.value.hasChildren()) {
				confirm("Reset changes in child blocks as well?").then((confirmed) => {
					block.value.resetChanges(confirmed);
				});
			} else {
				block.value.resetChanges();
			}
		},
		condition: () => block.value.isExtendedFromComponent(),
	},
	{
		label: "Sync Component",
		condition: () => Boolean(block.value.extendedFromComponent),
		action: () => {
			block.value.syncWithComponent();
		},
	},
	{
		label: "Reset Component",
		condition: () => Boolean(block.value.extendedFromComponent),
		action: () => {
			confirm("Are you sure you want to reset?").then((confirmed) => {
				if (confirmed) {
					block.value.resetWithComponent();
				}
			});
		},
	},
	{
		label: "Edit Component",
		action: () => {
			componentStore.editComponent(block.value);
		},
		condition: () => block.value.isExtendedFromComponent(),
	},
	{
		label: "Save as Block Template",
		action: () => {
			showBlockTemplateDialog.value = true;
		},
		condition: () => !block.value.isExtendedFromComponent() && Boolean(window.is_developer_mode),
	},
	{
		label: "Save As Component",
		action: () => (showNewComponentDialog.value = true),
		condition: () => !block.value.isExtendedFromComponent(),
	},
	{
		label: "Detach Component",
		action: () => {
			const newBlock = detachBlockFromComponent(block.value, null);
			if (newBlock) {
				newBlock.selectBlock();
			}
			block.value.getParentBlock()?.replaceChild(block.value, newBlock);
		},
		condition: () => Boolean(block.value.extendedFromComponent),
	},
	{
		label: "Rename",
		action: () => {
			const layerLabel = target.value?.closest("[data-block-layer-id]")?.querySelector(".layer-label");
			if (layerLabel) {
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
			}
		},
		condition: () =>
			!block.value.isRoot() && !block.value.isChildOfComponentBlock() && triggeredFromLayersPanel.value,
	},
	{
		label: "Delete",
		action: () => {
			canvasStore.activeCanvas?.removeBlock(block.value);
		},
		condition: () => {
			return (
				!block.value.isRoot() &&
				!block.value.isChildOfComponentBlock() &&
				block.value.isVisible() &&
				Boolean(block.value.getParentBlock())
			);
		},
	},
];

defineExpose({
	showContextMenu,
});
</script>
