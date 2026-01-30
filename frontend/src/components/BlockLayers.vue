<template>
	<div ref="rootContainer" class="relative">
		<draggable
			class="block-tree relative"
			:list="blocks"
			:group="{ name: 'block-tree', pull: 'clone', put: true }"
			item-key="blockId"
			@add="updateParent"
			:disabled="disableDraggable || readonly"
			:force-fallback="true"
			:fallback-class="'!hidden'"
			:fallback-on-body="false"
			:sort="false"
			:move="checkMove"
			@start="onDragStart"
			@end="onDragEnd">
			<template #item="{ element }">
				<div
					:data-block-layer-id="element.blockId"
					:data-indent="indent"
					:title="element.blockId"
					class="block-layer-item relative min-w-24 cursor-pointer select-none rounded border border-transparent bg-surface-white bg-opacity-50 text-base text-ink-gray-7"
					:class="{
						'border-blue-500 !bg-blue-100 dark:!bg-blue-900':
							canvasStore.layerDraggingOverBlock === element.blockId,
					}"
					@click.stop="selectBlock(element, $event)"
					@mouseover.stop="
						!canvasStore.isDragging && canvasStore.activeCanvas?.setHoveredBlock(element.blockId)
					"
					@mouseleave.stop="!canvasStore.isDragging && canvasStore.activeCanvas?.setHoveredBlock(null)">
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
							:contenteditable="element.editable && !readonly"
							:title="element.blockId"
							:class="{
								'text-purple-500 opacity-80 dark:opacity-100 dark:brightness-125 dark:saturate-[0.3]':
									element.isExtendedFromComponent(),
							}"
							@dblclick="
								(ev) => {
									if (!readonly) {
										element.editable = true;
										// focus
										const target = ev.target as HTMLElement;
										target.focus();
									}
								}
							"
							@keydown.enter.stop.prevent="element.editable = false"
							@blur="setBlockName($event, element)">
							{{ element.getBlockDescription() }}
						</span>
						<!-- toggle visibility -->
						<FeatherIcon
							v-if="!element.isRoot() && !isParentHidden && !readonly"
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
							:readonly="readonly"
							:disable-draggable="
								Boolean(element.children.length && element.children[0].isChildOfComponentBlock())
							" />
					</div>
				</div>
			</template>
		</draggable>
		<!-- Drop indicator line -->
		<div
			v-if="showDropIndicator"
			class="pointer-events-none absolute h-0.5 bg-blue-500 transition-none"
			:style="{
				top: dropIndicatorTop + 'px',
				left: dropIndicatorLeft + 'px',
				width: 'calc(100% - ' + dropIndicatorLeft + 'px)',
			}"></div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { FeatherIcon } from "frappe-ui";
import { ref, watch } from "vue";
import draggable from "vuedraggable";
import BlockLayers from "./BlockLayers.vue";
import BlocksIcon from "./Icons/Blocks.vue";

type LayerInstance = InstanceType<typeof BlockLayers>;

const canvasStore = useCanvasStore();

const rootContainer = ref<HTMLElement | null>(null);
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
		readonly?: boolean;
	}>(),
	{
		blocks: () => [],
		indent: 0,
		adjustForRoot: true,
		disableDraggable: false,
		isParentHidden: false,
		readonly: false,
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
	if (props.readonly) return;
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

interface DragState {
	draggedElement: HTMLElement | null;
	hoverTarget: HTMLElement | null;
	hoverPosition: "before" | "after" | "inside" | null;
}

const showDropIndicator = ref(false);
const dropIndicatorTop = ref(0);
const dropIndicatorLeft = ref(0);
const dragState: DragState = { draggedElement: null, hoverTarget: null, hoverPosition: null };

const resetDropIndicators = () => {
	showDropIndicator.value = false;
	canvasStore.layerDraggingOverBlock = null;
};

const checkMove = () => false; // Prevent automatic reordering

const onDragStart = (event: any) => {
	canvasStore.isDragging = true;
	resetDropIndicators();
	dragState.draggedElement = event.item;
	document.addEventListener("mousemove", onMouseMove);
};

const updateDropIndicator = (blockLayerItem: HTMLElement, relativeY: number, elementHeight: number) => {
	if (!rootContainer.value) return;

	const rect = blockLayerItem.getBoundingClientRect();
	const containerRect = rootContainer.value.getBoundingClientRect();
	const indent = parseInt(blockLayerItem.dataset.indent || "0", 10);
	const showAbove = relativeY < elementHeight / 2;

	dropIndicatorTop.value = showAbove ? rect.top - containerRect.top : rect.bottom - containerRect.top;
	dropIndicatorLeft.value = indent;
	dragState.hoverPosition = showAbove ? "before" : "after";
	showDropIndicator.value = true;
};

const onMouseMove = (event: MouseEvent) => {
	if (!dragState.draggedElement) return;

	const target = document.elementFromPoint(event.clientX, event.clientY);
	const blockLayerItem = target?.closest(".block-layer-item") as HTMLElement | null;

	if (!blockLayerItem || blockLayerItem === dragState.draggedElement) {
		resetDropIndicators();
		return;
	}

	const blockId = blockLayerItem.dataset.blockLayerId;
	const block = canvasStore.activeCanvas?.findBlock(blockId!);

	if (!block) {
		resetDropIndicators();
		return;
	}

	const rect = blockLayerItem.getBoundingClientRect();
	const relativeY = event.clientY - rect.top;
	const elementHeight = rect.height;
	const isInCenterZone = relativeY > elementHeight * 0.25 && relativeY < elementHeight * 0.75;

	dragState.hoverTarget = blockLayerItem;

	if (block.canHaveChildren() && isInCenterZone) {
		// Highlight parent block for nested drop
		canvasStore.layerDraggingOverBlock = blockId!;
		showDropIndicator.value = false;
		dragState.hoverPosition = "inside";
	} else {
		// Show line indicator for sibling drop
		canvasStore.layerDraggingOverBlock = null;
		updateDropIndicator(blockLayerItem, relativeY, elementHeight);
	}
};

const removeFromParent = (block: Block) => {
	const parent = block.getParentBlock();
	if (parent?.children) {
		const index = parent.children.indexOf(block);
		if (index > -1) parent.children.splice(index, 1);
	}
};

const moveBlockInside = (draggedBlock: Block, targetBlock: Block) => {
	removeFromParent(draggedBlock);
	if (!targetBlock.children) targetBlock.children = [];
	targetBlock.children.push(draggedBlock);
	draggedBlock.parentBlock = targetBlock;
};

const moveBlockAdjacent = (draggedBlock: Block, targetBlock: Block, position: "before" | "after") => {
	const targetParent = targetBlock.getParentBlock();
	if (!targetParent?.children) return;

	removeFromParent(draggedBlock);
	const targetIndex = targetParent.children.indexOf(targetBlock);
	const insertIndex = position === "before" ? targetIndex : targetIndex + 1;
	targetParent.children.splice(insertIndex, 0, draggedBlock);
	draggedBlock.parentBlock = targetParent;
};

const onDragEnd = () => {
	canvasStore.isDragging = false;
	resetDropIndicators();
	document.removeEventListener("mousemove", onMouseMove);

	const { draggedElement, hoverTarget, hoverPosition } = dragState;
	if (!draggedElement || !hoverTarget || !hoverPosition) {
		Object.assign(dragState, { draggedElement: null, hoverTarget: null, hoverPosition: null });
		return;
	}

	const draggedBlock = canvasStore.activeCanvas?.findBlock(draggedElement.dataset.blockLayerId!);
	const targetBlock = canvasStore.activeCanvas?.findBlock(hoverTarget.dataset.blockLayerId!);

	if (draggedBlock && targetBlock && draggedBlock !== targetBlock) {
		if (hoverPosition === "inside") {
			moveBlockInside(draggedBlock, targetBlock);
		} else {
			moveBlockAdjacent(draggedBlock, targetBlock, hoverPosition);
		}

		// Select the moved block
		canvasStore.activeCanvas?.selectBlock(draggedBlock);
	}

	Object.assign(dragState, { draggedElement: null, hoverTarget: null, hoverPosition: null });
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
