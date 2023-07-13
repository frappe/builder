<template>
	<div v-if="blocks.length">
		<draggable
			class="block-tree"
			:list="blocks"
			:group="{ name: 'block-tree' }"
			item-key="blockId"
			:disabled="blocks[0].isRoot()">
			<template #item="{ element }">
				<div
					class="cursor-pointer rounded border-[1px] bg-white pl-2 pr-[2px] text-sm text-gray-600 dark:bg-zinc-900"
					:class="{
						'border-transparent text-gray-700 dark:text-gray-500':
							!element.isSelected() && !element.isHovered(),
						'border-blue-200 text-gray-600 dark:border-blue-800 dark:text-gray-500':
							element.isHovered() && !element.isSelected(),
						'border-blue-400 text-gray-900 dark:border-blue-600 dark:text-gray-200': element.isSelected(),
					}"
					@click.stop="store.selectBlock(element, $event)"
					@mouseover.stop="store.hoveredBlock = element.blockId"
					@mouseleave.stop="store.hoveredBlock = null">
					<span class="my-[6px] flex items-center font-medium">
						<FeatherIcon
							:name="!element.collapsed ? 'chevron-down' : 'chevron-right'"
							class="mr-1 h-3 w-3"
							v-if="element.children && element.children.length && !element.isRoot()"
							@click.stop="element.collapsed = !element.collapsed" />
						<FeatherIcon :name="element.getIcon()" class="mr-1 h-3 w-3" />
						<span
							class="min-h-[1em] min-w-[2em] truncate"
							:contenteditable="element.editable"
							:title="element.blockId"
							@dblclick="element.editable = true"
							@keyup.enter.stop.prevent="element.editable = false"
							@blur="setBlockName($event, element)">
							{{ element.blockName || element.originalElement || element.element }}
							{{ element.innerText && !element.blockName ? " | " + element.innerText : "" }}
						</span>
					</span>
					<div v-if="element.children" v-show="!element.collapsed">
						<BlockLayers :blocks="element.children" class="ml-1" />
					</div>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup lang="ts">
import Block from "@/utils/block";
import { FeatherIcon } from "frappe-ui";
import { PropType } from "vue";
import draggable from "vuedraggable";
import useStore from "../store";

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
	block.blockName = target.innerText;
	block.editable = false;
};

const isExpanded = (block: Block) => {
	return block.isRoot() || block.isSelected() || block.children.some(isExpanded);
};
</script>
