<template>
	<div class="canvas bg-gray-100 min-h-screen">
		<h3>Canvas</h3>
		<div class="page"></div>
		<draggable
			:list="components"
			:group="{ name: 'widgets' }"
			item-key="id"
			class="w-full h-full flex-col flex"
		>
			<template #item="{ element }">
				<div class="flex items-center cursor-pointer justify-center h-12 w-24 border shadow-md rounded-md" :class="element.name">
					<span>{{ element.name }}</span>
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from 'vuedraggable';
import { ref } from 'vue';
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