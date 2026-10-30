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
			:delay="100"
			:delay-on-touch-only="false"
			:sort="false"
			:move="checkMove"
			@start="onDragStart"
			@end="onDragEnd">
			<template #item="{ element }">
				<div
					:data-block-layer-id="element.blockId"
					:data-indent="indent"
					:title="element.blockId"
					class="block-layer-item relative min-w-24 cursor-pointer select-none rounded-4 bg-surface-base bg-opacity-50 text-base text-ink-gray-7"
					@click.stop="selectBlock(element, $event)"
					@mouseover.stop="
						!canvasStore.isDragging && canvasStore.activeCanvas?.setHoveredBlock(element.blockId)
					"
					@mouseleave.stop="!canvasStore.isDragging && canvasStore.activeCanvas?.setHoveredBlock(null)">
					<span
						class="group flex py-[7px] items-center gap-1.5 pr-[2px] font-medium"
						:style="{ paddingLeft: `${indent}px` }"
						:class="{
							'!opacity-50': !element.isVisible() || isParentHidden,
							'rounded-4 !bg-surface-blue-4': canvasStore.layerDraggingOverBlock === element.blockId,
						}">
						<div>
							<div class="scroll-into-view-anchor absolute ml-20"></div>
						</div>
						<span
							:class="[
								isExpanded(element) ? 'lucide-chevron-down' : 'lucide-chevron-right',
								'h-3 w-3 text-ink-gray-4',
								{ 'ml-[-18px]': adjustForRoot },
							]"
							aria-hidden="true"
							v-if="
								element.children &&
								element.children.length &&
								!element.isRoot() &&
								element.editorConfig?.showChildrenInEditor !== false
							"
							@click="toggleExpanded(element)" />
						<span
							:class="[
								element.getIcon(),
								'h-3 w-3',
								{
									'text-purple-500 opacity-80 dark:opacity-100 dark:brightness-125 dark:saturate-[0.3]':
										element.isExtendedFromComponent(),
								},
							]"
							aria-hidden="true"
							v-if="!Boolean(element.extendedFromComponent)" />
						<span
							class="lucide-layout-dashboard mr-1 h-3 w-3"
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
						<span
							v-if="!element.isRoot() && !isParentHidden && !readonly"
							:class="[
								element.isVisible() ? 'lucide-eye' : 'lucide-eye-off',
								'invisible ml-auto mr-2 h-3 w-3 group-hover:visible',
							]"
							aria-hidden="true"
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
			v-if="!parentDropIndicator && dropIndicator.show"
			class="pointer-events-none absolute h-0.5 bg-blue-500 transition-none"
			:style="{
				top: dropIndicator.top + 'px',
				left: dropIndicator.left + 'px',
				right: dropIndicator.right + 'px',
			}"></div>
	</div>
</template>
<script setup lang="ts">
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { inject, nextTick, provide, Ref, ref, shallowReactive, watch } from "vue";
import draggable from "vuedraggable";
import BlockLayers from "./BlockLayers.vue";

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
	if (block.editorConfig?.showChildrenInEditor === false) {
		return false;
	}
	return (
		((isExpanded(block) && block.hasChildren()) || (block.canHaveChildren() && !block.hasChildren())) &&
		!block.isVideo()
	);
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

interface DropIndicator {
	show: boolean;
	top: number;
	left: number;
	right: number;
	treeRoot: Ref<HTMLElement | null>;
}

// The top-level tree draws the line, so a selected group's overflow-hidden cannot clip it.
const parentDropIndicator = inject<DropIndicator | null>("dropIndicator", null);
const dropIndicator =
	parentDropIndicator ?? shallowReactive({ show: false, top: 0, left: 0, right: 0, treeRoot: rootContainer });
if (!parentDropIndicator) provide("dropIndicator", dropIndicator);
const dragState: DragState = { draggedElement: null, hoverTarget: null, hoverPosition: null };

const resetDropIndicators = () => {
	dropIndicator.show = false;
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
	const treeRoot = dropIndicator.treeRoot.value;
	if (!treeRoot) return;

	const rect = blockLayerItem.getBoundingClientRect();
	const containerRect = treeRoot.getBoundingClientRect();
	const indent = parseInt(blockLayerItem.dataset.indent || "0", 10);
	const showAbove = relativeY < elementHeight / 2;

	dropIndicator.top = (showAbove ? rect.top : rect.bottom) - containerRect.top;
	dropIndicator.left = indent;
	dropIndicator.right = containerRect.right - rect.right;
	dragState.hoverPosition = showAbove ? "before" : "after";

	dropIndicator.show = indent === 0 && showAbove ? false : true;
};

const onMouseMove = (event: MouseEvent) => {
	const draggedElement = dragState.draggedElement;
	if (!draggedElement) return;

	const target = document.elementFromPoint(event.clientX, event.clientY);
	const blockLayerItem = target?.closest(".block-layer-item") as HTMLElement | null;

	if (!blockLayerItem || blockLayerItem === draggedElement || draggedElement.contains(blockLayerItem)) {
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
		dropIndicator.show = false;
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
	if (!draggedElement || !hoverTarget || !hoverPosition || draggedElement.contains(hoverTarget)) {
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

const getAllExpandableBlockIds = (blocks: Block[]): string[] => {
	const ids: string[] = [];
	for (const block of blocks) {
		if (!block.children?.length) continue;
		if (!block.isRoot() && block.editorConfig?.showChildrenInEditor !== false) {
			ids.push(block.blockId);
		}
		ids.push(...getAllExpandableBlockIds(block.children));
	}
	return ids;
};

const expandAll = async () => {
	const ids = getAllExpandableBlockIds(props.blocks);
	ids.forEach((id) => expandedLayers.value.add(id));
	await nextTick();
	childLayers.value.forEach((child) => child?.expandAll());
};

const collapseAll = () => {
	childLayers.value.forEach((child) => child?.collapseAll());
	expandedLayers.value.clear();
	expandedLayers.value.add("root");
};

defineExpose({
	toggleExpanded,
	isExpandedInTree,
	blockExitsInTree,
	expandAll,
	collapseAll,
});
</script>
<style>
.hovered-block > span {
	@apply rounded-4 bg-surface-blue-2;
}

.block-selected {
	@apply overflow-hidden !bg-surface-blue-1 text-ink-gray-9;
}

.block-selected > span {
	@apply rounded-none bg-surface-blue-3;
}

.block-selected .block-layer-item {
	@apply bg-transparent;
}

.block-selected .block-layer-item > span {
	@apply rounded-none;
}
</style>
