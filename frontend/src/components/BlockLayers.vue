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
							class="cursor-pointer rounded border bg-white pl-2 pr-[2px] text-sm text-gray-700 dark:bg-zinc-900"
							:class="{
								'border-transparent dark:text-gray-500': !element.isSelected() && !element.isHovered(),
								'border-blue-300 text-gray-700 dark:border-blue-800 dark:text-gray-500':
									element.isHovered() && !element.isSelected(),
								'border-blue-400 text-gray-900 dark:border-blue-600 dark:text-gray-200': element.isSelected(),
							}"
							@click.stop="
								element.expanded = true;
								store.selectBlock(element, $event, false);
							"
							@mouseover.stop="store.hoveredBlock = element.blockId"
							@mouseleave.stop="store.hoveredBlock = null">
							<span
								class="group my-[6px] flex items-center font-medium"
								:class="{
									'!opacity-50': !element.isVisible() || element.isChildOfComponentBlock(),
									'text-purple-500 opacity-80 dark:text-purple-400': element.isExtendedFromComponent(),
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
									v-if="!Boolean(element.extendedFromComponent)" />
								<svg
									class="mr-1 h-3 w-3"
									xmlns="http://www.w3.org/2000/svg"
									width="16"
									height="16"
									viewBox="0 0 24 24"
									v-if="Boolean(element.extendedFromComponent)">
									<g
										fill="none"
										stroke="currentColor"
										stroke-linecap="round"
										stroke-linejoin="round"
										stroke-width="2">
										<rect width="7" height="9" x="3" y="3" rx="1" />
										<rect width="7" height="5" x="14" y="3" rx="1" />
										<rect width="7" height="9" x="14" y="12" rx="1" />
										<rect width="7" height="5" x="3" y="16" rx="1" />
									</g>
								</svg>
								<span
									class="min-h-[1em] min-w-[2em] truncate"
									:contenteditable="element.editable"
									:title="element.blockId"
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
							<div v-show="isExpanded(element) && element.isVisible()">
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
			store.selectedBlocks.forEach((block) => {
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
