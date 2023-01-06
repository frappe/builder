<template>
	<div class="flex-col h-[2200px] bg-gray-100">
		<Toolbar class="z-10 relative"></Toolbar>
		<div class="flex justify-center">
			<div class="widgets bg-gray-200 w-1/5 z-10 relative p-5">
				<h3 class="mb-5">Widgets</h3>
				<draggable
					:list="widgets"
					:group="{ name: 'widgets', pull: 'clone', put: false }"
					item-key="id"
					class="w-full h-full flex-col flex"
				>
					<template #item="{ element }">
						<div class="flex items-center cursor-pointer justify-center h-12 w-24  border shadow-md rounded-md">
							<span>{{ element.name }}</span>
						</div>
					</template>
				</draggable>
			</div>
			<Canvas></Canvas>
			<div class="properties bg-gray-200 w-1/5 z-10 relative p-5">CSS</div>
		</div>
	</div>

</template>

<script setup>
import draggable from 'vuedraggable';
import { useStore } from "../store";
import { ref } from 'vue';
import Canvas from '../components/Canvas.vue';
import Toolbar from '../components/Toolbar.vue';

let widgets = ref([{
	id: 1,
	name: 'Container'
}, {
	id: 2,
	name: 'Text'
}, {
	id: 3,
	name: 'Image'
}])

</script>
<style>

</style>
