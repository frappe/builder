<template>
	<div class="ml-2">
		<div v-for="block in blocks">
			<div class="cursor-pointer text-sm px-2 py-1 truncate dark:text-gray-400 rounded-md"
				:class="{
					'border-blue-200 bg-transparent dark:border-blue-500 border-[1px]': store.hoveredBlock === block.blockId,
					'bg-none': !store.hoveredBlock === block.blockId,
					'border-blue-400 bg-transparent dark:border-blue-200 border-[1px]': store.builderState.selectedBlock === block
				}"
				@click.stop="selectBlock($event, block)"
				@mouseover.stop="store.hoveredBlock = block.blockId"
				@mouseleave.stop="store.hoveredBlock = null">
				{{ block.element }} {{ block.innerText ?  " | " + block.innerText : '' }}
				<div v-if="block.children">
					<BlockLayers :blocks="block.children"></BlockLayers>
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