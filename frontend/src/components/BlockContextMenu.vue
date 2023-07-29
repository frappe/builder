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
						v-model="componentProperties.isDynamicComponent"
						label="Is Dynamic" />
				</div>
			</template>
		</Dialog>
	</div>
</template>
<script setup lang="ts">
import webComponent from "@/data/webComponent";
import useStore from "@/store";
import { WebPageComponent } from "@/types/WebsiteBuilder/WebPageComponent";
import Block from "@/utils/block";
import Component from "@/utils/component";
import { copyToClipboard, getNumberFromPx } from "@/utils/helpers";
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
	isDynamicComponent: 0,
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

const copyBlocks = () => {
	// copy selected blocks to clipboard
	const selectedBlocks = store.builderState.selectedBlocks;
	copyToClipboard(JSON.stringify(selectedBlocks));
};

const pasteStyle = () => {
	props.block.updateStyles(store.copiedStyle?.style as BlockStyleObjects);
};

const duplicateBlock = () => {
	const blockCopy = store.getBlockCopy(props.block);
	const parentBlock = props.block.getParentBlock();

	if (blockCopy.getStyle("position") === "absolute") {
		// shift the block a bit
		const left = getNumberFromPx(blockCopy.getStyle("left"));
		const top = getNumberFromPx(blockCopy.getStyle("top"));
		blockCopy.setStyle("left", `${left + 20}px`);
		blockCopy.setStyle("top", `${top + 20}px`);
	}

	let child = null as Block | null;
	if (parentBlock) {
		child = parentBlock.addChildAfter(blockCopy, props.block);
	} else {
		child = store.builderState.blocks[0]?.addChild(blockCopy);
	}
	nextTick(() => {
		if (child) {
			child.selectBlock();
		}
	});
};

const createComponentHandler = ({ close }: { close: () => void }) => {
	const blockCopy = store.getBlockCopy(props.block);
	blockCopy.removeStyle("left");
	blockCopy.removeStyle("top");
	blockCopy.removeStyle("position");
	webComponent.insert
		.submit({
			block: blockCopy,
			component_name: componentProperties.value.componentName,
			is_dynamic: componentProperties.value.isDynamicComponent,
		})
		.then(async (data: WebPageComponent) => {
			await webComponent.list.promise;
			const block = store.findBlock(props.block.blockId);
			const component = new Component(webComponent.getRow(data.name).block);
			Object.assign(block, component);
		});
	close();
};

const contextMenuOptions: ContextMenuOption[] = [
	{ label: "Copy", action: copyBlocks },
	{ label: "Copy Style", action: copyStyle },
	{
		label: "Paste Style",
		action: pasteStyle,
		condition: () => Boolean(store.copiedStyle && store.copiedStyle.blockId !== props.block.blockId),
	},
	{
		label: "Save as Component",
		action: () => (showDialog.value = true),
		condition: () => !props.block.isComponent,
	},
	{ label: "Duplicate", action: duplicateBlock },
];
</script>
