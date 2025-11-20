<template>
	<div>
		<draggable
			class="block-tree"
			:list="blocks"
			:group="{ name: 'block-tree' }"
			item-key="blockId"
			@add="updateParent"
			@end="handleDragEnd"
			:move="handleDragMove"
			:disabled="disableDraggable">
			<template #item="{ element }">
				<div
					:data-block-layer-id="element.blockId"
					:title="element.blockId"
					class="min-w-24 cursor-pointer select-none rounded border border-transparent bg-surface-white bg-opacity-50 text-base text-ink-gray-7"
					@click.stop="selectBlock(element, $event)"
					@mouseover.stop="canvasStore.activeCanvas?.setHoveredBlock(element.blockId)"
					@mouseleave.stop="canvasStore.activeCanvas?.setHoveredBlock(null)">
					<span
						class="group my-[7px] flex items-center gap-1.5 pr-[2px] font-medium"
						:style="{ paddingLeft: `${indent}px` }"
						:class="{
							'!opacity-50': !element.isVisible() || isParentHidden,
						}">
						<div>
							<div class="scroll-into-view-anchor absolute ml-20"></div>
						</div>
						<FeatherIcon
							:name="isExpanded(element) ? 'chevron-down' : 'chevron-right'"
							class="h-3 w-3 text-ink-gray-4"
							:class="{
								'ml-[-18px]': adjustForRoot,
							}"
							v-if="element.children && element.children.length && !element.isRoot()"
							@click.stop="toggleExpanded(element)" />
						<FeatherIcon
							:name="element.getIcon()"
							class="h-3 w-3"
							:class="{
								'text-purple-500 opacity-80 dark:opacity-100 dark:brightness-125 dark:saturate-[0.3]':
									element.isExtendedFromComponent(),
							}"
							v-if="!Boolean(element.extendedFromComponent)" />
						<BlocksIcon
							class="mr-1 h-3 w-3"
							:class="{
								'text-purple-500 opacity-80 dark:opacity-100 dark:brightness-125 dark:saturate-[0.3]':
									element.isExtendedFromComponent(),
							}"
							v-if="Boolean(element.extendedFromComponent)" />
						<span
							class="layer-label min-h-[1em] min-w-[2em] max-w-64 truncate"
							:contenteditable="element.editable"
							:title="element.blockId"
							:class="{
								'text-purple-500 opacity-80 dark:opacity-100 dark:brightness-125 dark:saturate-[0.3]':
									element.isExtendedFromComponent(),
							}"
							@dblclick="
								(ev) => {
									element.editable = true;
									// focus
									const target = ev.target as HTMLElement;
									target.focus();
								}
							"
							@keydown.enter.stop.prevent="element.editable = false"
							@blur="setBlockName($event, element)">
							{{ element.getBlockDescription() }}
						</span>
						<!-- toggle visibility -->
						<FeatherIcon
							v-if="!element.isRoot() && !isParentHidden"
							:name="element.isVisible() ? 'eye' : 'eye-off'"
							class="invisible ml-auto mr-2 h-3 w-3 group-hover:visible"
							@click.stop="element.toggleVisibility()" />
					</span>
					<div v-if="canShowChildLayer(element)">
						<BlockLayers
							:blocks="element.children"
							:ref="childLayer"
							:is-parent-hidden="isParentHidden || !element.isVisible()"
							:indent="childIndent"
							:disable-draggable="
								Boolean(element.children.length && element.children[0].isChildOfComponentBlock())
							" />
					</div>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { FeatherIcon } from "frappe-ui";
import { nextTick, ref, watch } from "vue";
import draggable from "vuedraggable";
import BlockLayers from "./BlockLayers.vue";
import BlocksIcon from "./Icons/Blocks.vue";
import blockController from "@/utils/blockController";

type LayerInstance = InstanceType<typeof BlockLayers>;

const canvasStore = useCanvasStore();
const builderStore = useBuilderStore();

const childLayers = ref<LayerInstance[]>([]);
const childLayer = (el: LayerInstance) => {
	if (el) {
		childLayers.value.push(el);
	}
};

const props = withDefaults(
	defineProps<{
		blocks: Block[];
		indent?: number;
		adjustForRoot?: boolean;
		disableDraggable?: boolean;
		isParentHidden?: boolean;
	}>(),
	{
		blocks: () => [],
		indent: 0,
		adjustForRoot: true,
		disableDraggable: false,
		isParentHidden: false,
	},
);

interface LayerBlock extends Block {
	editable: boolean;
}

let childIndent = props.indent + 24;
if (!props.adjustForRoot) {
	childIndent = props.indent + 32;
}

const setBlockName = (ev: Event, block: LayerBlock) => {
	const target = ev.target as HTMLElement;
	block.blockName = target.innerText.trim();
	block.editable = false;
};

const expandedLayers = ref(new Set(["root"]));

const isExpanded = (block: Block) => {
	return expandedLayers.value.has(block.blockId);
};

// TODO: Refactor this!
const toggleExpanded = (block: Block) => {
	if (block.isRoot()) {
		return;
	}
	if (!blockExits(block)) {
		const child = childLayers.value.find((layer) => layer.blockExitsInTree(block)) as LayerInstance;
		if (child) {
			child.toggleExpanded(block);
		}
	}
	if (isExpanded(block)) {
		expandedLayers.value.delete(block.blockId);
	} else {
		expandedLayers.value.add(block.blockId);
	}
};

// @ts-ignore
const isExpandedInTree = (block: Block) => {
	if (!blockExits(block)) {
		const child = childLayers.value.find((layer) => layer.blockExitsInTree(block)) as LayerInstance;
		if (child) {
			return child.isExpandedInTree(block);
		}
	}
	return isExpanded(block);
};

const blockExits = (block: Block) => {
	return props.blocks.find((b) => b.blockId === block.blockId);
};

const canShowChildLayer = (block: Block) => {
	return (isExpanded(block) && block.hasChildren()) || (block.canHaveChildren() && !block.hasChildren());
};

watch(
	() => canvasStore.activeCanvas?.selectedBlockIds,
	() => {
		if (canvasStore.activeCanvas?.selectedBlocks.length) {
			canvasStore.activeCanvas?.selectedBlocks.forEach((block: Block) => {
				if (block) {
					let parentBlock = block.getParentBlock();
					// open all parent blocks
					while (parentBlock && !parentBlock.isRoot()) {
						expandedLayers.value.add(parentBlock?.blockId);
						parentBlock = parentBlock.getParentBlock();
					}
				}
			});
		}
	},
	{ immediate: true, deep: true },
);

// @ts-ignore
const updateParent = (event) => {
	event.item.__draggable_context.element.parentBlock = canvasStore.activeCanvas?.findBlock(
		event.to.closest("[data-block-layer-id]").dataset.blockLayerId,
	);
};

const blockExitsInTree = (block: Block) => {
	if (blockExits(block)) {
		return true;
	}
	for (const layer of childLayers.value) {
		if (layer.blockExitsInTree(block)) {
			return true;
		}
	}
	return false;
};

const selectBlock = (block: Block, event: MouseEvent) => {
	canvasStore.selectBlock(block, event, false, true);
};

const currentlyDraggingBlock = ref<Block | null>(null);

const handleDragMove = (event: any) => {
	const draggedBlock: Block = event.draggedContext.element;
	if (!currentlyDraggingBlock.value) {
		currentlyDraggingBlock.value = draggedBlock;

		const canvasStore = useCanvasStore();
		const pauseId = canvasStore.activeCanvas?.history?.pause();
		
		const listOfInheritedProps = [];
		for (const propKey in draggedBlock.props) {
			if (draggedBlock.props[propKey].type === "inherited" && draggedBlock.props[propKey].value) {
				listOfInheritedProps.push(draggedBlock.props[propKey].value);
			}
		}
		blockController.updateBlockPropsDependencyForAncestor(listOfInheritedProps, "remove", draggedBlock);

		nextTick(() => {
			pauseId && canvasStore.activeCanvas?.history?.resume(pauseId);
		});
	}
	return true; // Allow the move
};

const handleDragEnd = async () => {
	await nextTick();
	if (currentlyDraggingBlock.value) {
		const listOfInheritedProps = [];
		for (const propKey in currentlyDraggingBlock.value.props) {
			if (
				currentlyDraggingBlock.value.props[propKey].type === "inherited" &&
				currentlyDraggingBlock.value.props[propKey].value
			) {
				listOfInheritedProps.push(currentlyDraggingBlock.value.props[propKey].value);
			}
		}
		blockController.updateBlockPropsDependencyForAncestor(
			listOfInheritedProps,
			"add",
			currentlyDraggingBlock.value,
		);
		currentlyDraggingBlock.value = null;
	}
};

defineExpose({
	toggleExpanded,
	isExpandedInTree,
	blockExitsInTree,
});
</script>
<style>
.hovered-block {
	@apply border-blue-300 text-gray-700 dark:border-blue-900 dark:text-gray-500;
}
.block-selected {
	@apply border-blue-400 text-gray-900 dark:border-blue-700 dark:text-gray-200;
}
</style>
