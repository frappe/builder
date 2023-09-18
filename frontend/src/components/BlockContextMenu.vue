<template>
	<div>
		<slot :onContextMenu="showContextMenu" />
		<ContextMenu
			v-if="contextMenuVisible"
			:pos-x="posX"
			:pos-y="posY"
			:options="contextMenuOptions"
			@select="handleContextMenuSelect"
			v-on-click-outside="() => (contextMenuVisible = false)" />
		<Dialog
			style="z-index: 40"
			:options="{
				title: 'New Component',
				size: 'sm',
				actions: [
					{
						label: 'Save',
						appearance: 'primary',
						onClick: createComponentHandler,
					},
					{ label: 'Cancel' },
				],
			}"
			v-model="showDialog">
			<template #body-content>
				<Input type="text" v-model="componentProperties.componentName" label="Component Name" required />
				<div class="mt-3">
					<Input
						class="text-sm [&>span]:!text-sm"
						type="checkbox"
						v-model="componentProperties.isGlobalComponent"
						label="Global Component" />
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { BuilderComponent } from "@/types/WebsiteBuilder/BuilderComponent";
import Block from "@/utils/block";
import getBlockTemplate from "@/utils/blockTemplate";
import { vOnClickOutside } from "@vueuse/components";
import { Dialog } from "frappe-ui";
import { nextTick, ref } from "vue";
import ContextMenu from "./ContextMenu.vue";
const store = useStore();

const props = defineProps<{
	block: Block;
	editable: boolean;
}>();

const contextMenuVisible = ref(false);
const posX = ref(0);
const posY = ref(0);

const showDialog = ref(false);

const componentProperties = ref({
	componentName: "",
	isGlobalComponent: 0,
});

const showContextMenu = (event: MouseEvent) => {
	if (props.block.isRoot() || props.editable) return;
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

const copyStyle = () => {
	store.copiedStyle = {
		blockId: props.block.blockId,
		style: props.block.getStylesCopy(),
	};
};

const pasteStyle = () => {
	props.block.updateStyles(store.copiedStyle?.style as BlockStyleObjects);
};

const duplicateBlock = () => {
	props.block.duplicateBlock();
};

const createComponentHandler = ({ close }: { close: () => void }) => {
	const blockCopy = store.getBlockCopy(props.block, true);
	blockCopy.removeStyle("left");
	blockCopy.removeStyle("top");
	blockCopy.removeStyle("position");
	webComponent.insert
		.submit({
			block: blockCopy,
			component_name: componentProperties.value.componentName,
			for_web_page: componentProperties.value.isGlobalComponent ? null : store.getActivePage()?.name,
		})
		.then(async (data: BuilderComponent) => {
			await webComponent.list.promise;
			const block = store.findBlock(props.block.blockId);
			if (!block) return;
			block.extendFromComponent(data.name);
		});
	close();
};

const contextMenuOptions: ContextMenuOption[] = [
	{ label: "Copy", action: () => document.execCommand("copy") },
	{ label: "Copy Style", action: copyStyle },
	{
		label: "Paste Style",
		action: pasteStyle,
		condition: () => Boolean(store.copiedStyle && store.copiedStyle.blockId !== props.block.blockId),
	},
	{ label: "Duplicate", action: duplicateBlock },
	{
		label: "Wrap in Container",
		action: () => {
			const newBlockObj = getBlockTemplate("fit-container");
			const parentBlock = props.block.getParentBlock();
			if (!parentBlock) return;

			const selectedBlocks = store.selectedBlocks;
			const blockPosition = Math.min(...selectedBlocks.map(parentBlock.getChildIndex.bind(parentBlock)));
			const newBlock = parentBlock?.addChild(newBlockObj, blockPosition);

			// move selected blocks to newBlock
			selectedBlocks.forEach((block) => {
				parentBlock?.removeChild(block);
				newBlock?.addChild(block);
			});

			nextTick(() => {
				if (newBlock) {
					newBlock.selectBlock();
				}
			});
		},
		condition: () => {
			if (props.block.isRoot()) return false;
			if (store.selectedBlocks.length === 1) return true;
			// check if all selected blocks are siblings
			const parentBlock = props.block.getParentBlock();
			if (!parentBlock) return false;
			const selectedBlocks = store.selectedBlocks;
			return selectedBlocks.every((block) => block.getParentBlock() === parentBlock);
		},
	},
	{
		label: "Save as Component",
		action: () => (showDialog.value = true),
		condition: () => !props.block.isExtendedFromComponent(),
	},
	{
		label: "Convert To Repeater",
		action: () => {
			props.block.convertToRepeater();
		},
		condition: () =>
			props.block.isContainer() && !props.block.isExtendedFromComponent() && !props.block.isRoot(),
	},
	{
		label: "Reset Changes",
		condition: () => Boolean(props.block.extendedFromComponent),
		action: () => {
			props.block.resetChanges();
		},
	},
	{
		label: "Edit Component",
		action: () => {
			store.editComponent(props.block);
		},
		condition: () => props.block.isExtendedFromComponent(),
	},
	// convert to link
	{
		label: "Convert to Link",
		action: () => {
			blockController.getSelectedBlocks().forEach((block) => {
				block.convertToLink();
			});
		},
		condition: () =>
			(props.block.isContainer() || props.block.isText()) &&
			!props.block.isExtendedFromComponent() &&
			!props.block.isRoot(),
	},
];
</script>
