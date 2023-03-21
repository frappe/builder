<template>
	<div class="ml-1">
		<draggable
			class="block-tree"
			:list="blocks"
			:group="{ name: 'block-tree' }"
			item-key="blockId"
		>
			<template #item="{ element }">
				<div class="cursor-pointer text-base pl-2 pr-[2px] py-1 rounded-md border-[1px]"
					:class="{
							// TODO: simplify this
							'border-transparent text-gray-600 dark:text-gray-500': store.builderState.selectedBlock && store.builderState.selectedBlock.blockId !== element.blockId && store.hoveredBlock !== element.blockId,
							'border-blue-200 dark:border-blue-800 text-gray-600 dark:text-gray-500': store.hoveredBlock === element.blockId && store.builderState.selectedBlock && store.builderState.selectedBlock.blockId !== element.blockId,
							'border-blue-400 dark:border-blue-600 text-gray-900 dark:text-gray-200': store.builderState.selectedBlock && store.builderState.selectedBlock.blockId === element.blockId,
						}"
						@click.stop="selectBlock($event, element)"
						@mouseover.stop="store.hoveredBlock = element.blockId"
						@mouseleave.stop="store.hoveredBlock = null">
						<span class="flex items-center">
							<FeatherIcon :name="element.getIcon()" class="h-3 w-3 mr-1 text-gray-500"></FeatherIcon>
							<span class="truncate">
								{{ element.element }} {{ element.innerText ?  " | " + element.innerText : '' }}
							</span>
						</span>
						<div v-if="element.children">
							<BlockLayers :blocks="element.children"></BlockLayers>
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
defineProps(["blocks"]);
const selectBlock = (e, block) => {
	store.builderState.selectedBlock = block;
};
</script>