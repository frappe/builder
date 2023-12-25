<template>
	<div>
		<draggable
			class="block-tree"
			:list="blocks"
			:group="{ name: 'block-tree' }"
			item-key="blockId"
			:disabled="blocks.length && (blocks[0].isRoot() || blocks[0].isChildOfComponentBlock())">
			<template #item="{ element }">
				<div>
					<BlockContextMenu v-slot="{ onContextMenu }" :block="element" :editable="false">
						<div
							:data-block-layer-id="element.blockId"
							:title="element.blockId"
							@contextmenu.prevent.stop="onContextMenu"
							class="cursor-pointer rounded border border-transparent bg-white pl-2 pr-[2px] text-sm text-gray-700 dark:bg-zinc-900 dark:text-gray-500"
							:class="{
								'block-selected': element.isSelected(),
							}"
							@click.stop="
								store.activeCanvas?.history.pause();
								element.expanded = true;
								store.selectBlock(element, $event, false);
								store.activeCanvas?.history.resume();
							"
							@mouseover.stop="store.hoveredBlock = element.blockId"
							@mouseleave.stop="store.hoveredBlock = null">
							<span
								class="group my-[6px] flex items-center font-medium"
								:class="{
									'!opacity-50': !element.isVisible(),
								}">
								<FeatherIcon
									:name="isExpanded(element) ? 'chevron-down' : 'chevron-right'"
									class="mr-1 h-3 w-3"
									v-if="
										element.children &&
										element.children.length &&
										!element.isRoot() &&
										!element.isImage() &&
										!element.isSVG()
									"
									@click.stop="toggleExpanded(element)" />
								<FeatherIcon
									:name="element.getIcon()"
									class="mr-1 h-3 w-3"
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
								<span v-if="element.isRoot()" class="ml-auto mr-2 text-gray-400 dark:text-zinc-600">
									{{ store.activeBreakpoint }}
								</span>
							</span>
							<div
								v-show="
									isExpanded(element) &&
									element.isVisible() &&
									!element.isSVG() &&
									!element.isImage() &&
									!(element.isText() && !element.isLink())
								">
								<BlockLayers :blocks="element.children" class="ml-3" />
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
import BlocksIcon from "./Icons/Blocks.vue";

const store = useStore();

defineProps({
	blocks: {
		type: Array as PropType<Block[]>,
		default: () => [],
	},
});

interface LayerBlock extends Block {
	editable: boolean;
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

const toggleExpanded = (block: Block) => {
	if (isExpanded(block) && !block.isRoot()) {
		expandedLayers.value.delete(block.blockId);
	} else {
		expandedLayers.value.add(block.blockId);
	}
};

watch(
	() => store.selectedBlocks,
	() => {
		if (store.selectedBlocks.length) {
			store.selectedBlocks.forEach((block: Block) => {
				if (block) {
					expandedLayers.value.add(block.blockId);
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
	{ immediate: true }
);
</script>
<style>
.hovered-block {
	@apply border-blue-300 text-gray-700 dark:border-blue-800 dark:text-gray-500;
}
.block-selected {
	@apply border-blue-400 text-gray-900 dark:border-blue-600 dark:text-gray-200;
}
</style>
