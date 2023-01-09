<template>
	<div class="canvas min-h-screen w-3/4 h-screen p-10 flex justify-center" ref="canvas_container">
		<div class="h-full flex-col flex page bg-white rounded-md w-[1024px]"
			ref="canvas">
			<draggable
				:list="components"
				:group="{ name: 'widgets' }"
				item-key="id"
				class="w-full h-full flex-col flex"
			>
				<template #item="{ element }">
					<div class="flex items-center cursor-pointer justify-center h-12 w-24 border rounded-md" :class="element.name">
						<span>{{ element.name }}</span>
					</div>
				</template>
			</draggable>
		</div>
	</div>
</template>
<script setup>
import { onMounted, ref } from 'vue';
import draggable from 'vuedraggable';
import { useStore } from "../store";
import { pan, zoom } from '../utils/panandzoom.js';

const canvas_container = ref(null);
const canvas = ref(null);

onMounted(() => {
	console.log('canvas', canvas.value);
	pan(canvas.value)
	zoom(canvas_container.value)
})

let store = useStore();
let components = ref([]);
</script>
<style>
@tailwind components;
@layer components {
	.Container {
		@apply bg-gray-300;
		@apply h-[300px];
		@apply w-full;
	}
	.Text {
		color: black;
		background: none;
		border: none;
		box-shadow: none;
	}
	.Image {
		@apply bg-gray-600;
		@apply h-[300px];
		@apply w-[500px];
	}
}

</style>