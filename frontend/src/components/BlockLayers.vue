<template>
	<div>
		<draggable
			class="block-tree"
			:list="blocks"
			:group="{ name: 'block-tree' }"
			item-key="blockId"
			@add="updateParent"
			:disabled="blocks.length && (blocks[0].isRoot() || blocks[0].isChildOfComponentBlock())">
			<template #item="{ element }">
				<div>
					<BlockContextMenu v-slot="{ onContextMenu }" :block="element" :editable="false">
						<div
							:data-block-layer-id="element.blockId"
							:title="element.blockId"
							@contextmenu.prevent.stop="onContextMenu"
							class="min-w-24 cursor-pointer overflow-hidden rounded border border-transparent bg-surface-white bg-opacity-50 text-base text-ink-gray-7"
							@click.stop="
								store.activeCanvas?.history.pause();
								store.selectBlock(element, $event, false, true);
								store.activeCanvas?.history.resume();
							"
							@mouseover.stop="store.hoveredBlock = element.blockId"
							@mouseleave.stop="store.hoveredBlock = null">
							<span
								class="group my-[7px] flex items-center gap-1.5 pr-[2px] font-medium"
								:style="{ paddingLeft: `${indent}px` }"
								:class="{
									'!opacity-50': !element.isVisible(),
								}">
								<FeatherIcon
									:name="isExpanded(element) ? 'chevron-down' : 'chevron-right'"
									class="ml-[-18px] h-3 w-3 text-ink-gray-4"
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
									class="min-h-[1em] min-w-[2em] truncate"
									:contenteditable="element.editable"
									:title="element.blockId"
									:class="{
										'text-purple-500 opacity-80 dark:opacity-100 dark:brightness-125 dark:saturate-[0.3]':
											element.isExtendedFromComponent(),
									}"
									@dblclick="element.editable = true"
									@keydown.enter.stop.prevent="element.editable = false"
									@blur="setBlockName($event, element)">
									{{ element.getBlockDescription() }}
								</span>
								<!-- toggle visibility -->
								<FeatherIcon
									v-if="!element.isRoot()"
									:name="element.isVisible() ? 'eye' : 'eye-off'"
									class="ml-auto mr-2 hidden h-3 w-3 group-hover:block"
									@click.stop="element.toggleVisibility()" />
								<span v-if="element.isRoot()" class="ml-auto mr-2 text-sm capitalize text-ink-gray-5">
									{{ store.activeBreakpoint }}
								</span>
							</span>
							<div v-show="canShowChildLayer(element)">
								<BlockLayers :blocks="element.children" :ref="childLayer" :indent="childIndent" />
							</div>
						</div>
					</BlockContextMenu>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { FeatherIcon } from "frappe-ui";
import { PropType, ref, watch } from "vue";
import draggable from "vuedraggable";
import useStore from "../store";
import BlockContextMenu from "./BlockContextMenu.vue";
import BlockLayers from "./BlockLayers.vue";
import BlocksIcon from "./Icons/Blocks.vue";

type LayerInstance = InstanceType<typeof BlockLayers>;

const store = useStore();
const childLayers = ref<LayerInstance[]>([]);
const childLayer = (el) => {
	if (el) {
		childLayers.value.push(el);
	}
};

const props = defineProps({
	blocks: {
		type: Array as PropType<Block[]>,
		default: () => [],
	},
	indent: {
		type: Number,
		default: 10,
	},
});

interface LayerBlock extends Block {
	editable: boolean;
}

const childIndent = props.indent + 16;

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
	return (
		((isExpanded(block) && block.hasChildren()) || (block.canHaveChildren() && !block.hasChildren())) &&
		block.isVisible()
	);
};

watch(
	() => store.activeCanvas?.selectedBlocks,
	() => {
		if (store.activeCanvas?.selectedBlocks.length) {
			store.activeCanvas?.selectedBlocks.forEach((block: Block) => {
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
);

// @ts-ignore
const updateParent = (event) => {
	event.item.__draggable_context.element.parentBlock = store.activeCanvas?.findBlock(
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
