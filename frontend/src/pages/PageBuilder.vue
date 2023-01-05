<template>
	<div class="flex-col h-screen">
		<Grid></Grid>
		<Toolbar></Toolbar>
		<div class="flex h-full">
			<div class="widgets bg-gray-200 w-1/5">
				<h3>Widgets</h3>
				<draggable
					:list="widgets"
					:group="{ name: 'widgets', pull: 'clone', put: false }"
					item-key="id"
					class="w-full h-full flex-col flex items-center"
				>
					<template #item="{ element }">
						<div class="flex items-center cursor-pointer justify-center h-12 w-24  border shadow-md rounded-md">
							<span>{{ element.name }}</span>
						</div>
					</template>
				</draggable>
			</div>
			<Canvas class="w-3/5"></Canvas>
			<div class="properties bg-gray-200 w-1/5">CSS</div>
		</div>
	</div>

</template>

<script setup>
import draggable from 'vuedraggable';
import { ref } from 'vue';
import Canvas from '../components/Canvas.vue';
import Toolbar from '../components/Toolbar.vue';
import Grid from '../components/Grid.vue';

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
