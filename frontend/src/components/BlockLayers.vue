<template>
	<div>
		<div v-for="block in blocks">
			<div class="cursor-pointer text-base p-[2px] truncate dark:text-gray-400"
				:class="{
					'bg-blue-50 dark:bg-transparent dark:border-blue-300 dark:border-[1px]': store.hoveredBlock === block.blockId,
					'bg-none': !store.hoveredBlock === block.blockId,
					'bg-blue-50 dark:bg-transparent dark:border-blue-200 dark:border-[1px]': store.builderState.selectedBlock === block
				}"
				@click.stop="selectBlock($event, block)"
				@mouseover.stop="store.hoveredBlock = block.blockId"
				@mouseleave.stop="store.hoveredBlock = null">
				{{ block.element }}
				<div v-if="block.children">
					<BlockLayers :blocks="block.children" class="ml-4"></BlockLayers>
				</div>
			</div>
		</div>
	</div>
</template>
<script setup>
import useStore from "../store";
const store = useStore();
defineProps(["blocks"]);
const selectBlock = (e, block) => {
	store.builderState.selectedBlock = block;
};
</script>