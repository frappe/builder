<template>
	<div class="ml-1">
		<draggable class="block-tree" :list="blocks" :group="{ name: 'block-tree' }" item-key="blockId">
			<template #item="{ element }">
				<div
					class="cursor-pointer rounded-md border-[1px] bg-white py-1 pl-2 pr-[2px] text-base text-gray-600 dark:bg-zinc-900"
					:class="{
						// TODO: simplify this
						'border-transparent text-gray-700 dark:text-gray-500':
							(store.builderState.selectedBlock &&
								store.builderState.selectedBlock.blockId !== element.blockId &&
								store.hoveredBlock !== element.blockId) ||
							!store.builderState.selectedBlock,
						'border-blue-200 text-gray-600 dark:border-blue-800 dark:text-gray-500':
							store.hoveredBlock === element.blockId &&
							store.builderState.selectedBlock &&
							store.builderState.selectedBlock.blockId !== element.blockId,
						'border-blue-400 text-gray-900 dark:border-blue-600 dark:text-gray-200':
							store.builderState.selectedBlock &&
							store.builderState.selectedBlock.blockId === element.blockId,
					}"
					@click.stop="selectBlock($event, element)"
					@mouseover.stop="store.hoveredBlock = element.blockId"
					@mouseleave.stop="store.hoveredBlock = null">
					<span class="flex items-center font-medium">
						<FeatherIcon
							:name="element.fold ? 'chevron-right' : 'chevron-down'"
							class="mr-1 h-3 w-3"
							v-if="element.children && element.children.length && !element.isRoot()"
							@click.stop="element.fold = !element.fold" />
						<FeatherIcon :name="element.getIcon()" class="mr-1 h-3 w-3" />
						<span class="truncate">
							{{ element.originalElement || element.element }}
							{{ element.innerText ? " | " + element.innerText : "" }}
						</span>
					</span>
					<div v-if="element.children" v-show="!element.fold">
						<BlockLayers :blocks="element.children" />
					</div>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import { FeatherIcon } from "frappe-ui";
import draggable from "vuedraggable";
import useStore from "../store";
const store = useStore();
defineProps({
	blocks: {
		type: Array,
		default: () => [],
	},
});
const selectBlock = (e, block) => {
	store.builderState.selectedBlock = block;
};
</script>
