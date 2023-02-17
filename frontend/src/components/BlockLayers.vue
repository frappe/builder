<template>
	<div>
		<div v-for="block in blocks">
			<div class="cursor-pointer text-base"
				:class="{
					'bg-gray-200': block.hover,
					'bg-white': !block.hover,
					'border-2 border-blue-200': store.selectedBlock === block
				}"
				@click.stop="selectBlock($event, block)"
				@mouseover.stop="block.hover = true"
				@mouseleave.stop="block.hover = false">
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
	store.selectedBlock = block;
};
</script>