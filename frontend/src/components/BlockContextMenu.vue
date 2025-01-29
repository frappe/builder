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
import ContextMenu from "@/components/ContextMenu.vue";
import NewBlockTemplate from "@/components/Modals/NewBlockTemplate.vue";
import NewComponent from "@/components/Modals/NewComponent.vue";
import useStore from "@/store";
import Block from "@/utils/block";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import { confirm, detachBlockFromComponent, getBlockCopy } from "@/utils/helpers";
import useComponentStore from "@/utils/useComponentStore";
import { vOnClickOutside } from "@vueuse/components";
import { useStorage } from "@vueuse/core";
import { Ref, nextTick, ref } from "vue";
import { toast } from "vue-sonner";

const store = useStore();
const componentStore = useComponentStore();

const contextMenuVisible = ref(false);
const posX = ref(0);
const posY = ref(0);

const block = ref(null) as unknown as Ref<Block>;

const showNewComponentDialog = ref(false);
const showBlockTemplateDialog = ref(false);

const showContextMenu = (event: MouseEvent, refBlock: Block) => {
	block.value = refBlock;
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
			store.editHTML(block.value);
		},
		condition: () => block.value.isHTML(),
	},
	{ label: "Copy", action: () => document.execCommand("copy") },
	{ label: "Copy Style", action: copyStyle },
	{
		label: "Paste Style",
		action: pasteStyle,
		condition: () => Boolean(copiedStyle.value.blockId && copiedStyle.value?.blockId !== block.value.blockId),
	},
	{ label: "Duplicate", action: duplicateBlock },
	{
		label: "Convert To Link",
		action: () => {
			blockController.convertToLink();
		},
		condition: () =>
			(block.value.isContainer() || block.value.isText() || block.value.isImage()) &&
			!block.value.isLink() &&
			!block.value.isExtendedFromComponent() &&
			!block.value.isRoot(),
	},
	{
		label: "Wrap In Container",
		action: () => {
			const newBlockObj = getBlockTemplate("fit-container");
			const parentBlock = block.value.getParentBlock();
			if (!parentBlock) return;

			const selectedBlocks = store.activeCanvas?.selectedBlocks || [];
			const blockPosition = Math.min(...selectedBlocks.map(parentBlock.getChildIndex.bind(parentBlock)));
			const newBlock = parentBlock?.addChild(newBlockObj, blockPosition);

			let width = null as string | null;
			// move selected blocks to newBlock
			selectedBlocks
				.sort((a, b) => parentBlock.getChildIndex(a) - parentBlock.getChildIndex(b))
				.forEach((block) => {
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
			if (store.activeCanvas?.selectedBlocks.length === 1) return true;
			// check if all selected blocks are siblings
			const parentBlock = block.value.getParentBlock();
			if (!parentBlock) return false;
			const selectedBlocks = store.activeCanvas?.selectedBlocks || [];
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
			store.propertyFilter = "data key";
			toast.warning("Please set data key for repeater block");
		},
		condition: () => !block.value.isRoot() && !block.value.isRepeater(),
	},
	{
		label: "Reset Overrides",
		condition: () => store.activeBreakpoint !== "desktop",
		disabled: () => !block.value?.hasOverrides(store.activeBreakpoint),
		action: () => {
			block.value.resetOverrides(store.activeBreakpoint);
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
		condition: () => Boolean(block.value.extendedFromComponent),
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
			const newBlock = detachBlockFromComponent(block.value);
			if (newBlock) {
				newBlock.selectBlock();
			}
			block.value.getParentBlock()?.replaceChild(block.value, newBlock);
		},
		condition: () => Boolean(block.value.extendedFromComponent),
	},
	{
		label: "Delete",
		action: () => {
			store.activeCanvas?.removeBlock(block.value);
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
