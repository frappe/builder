<template>
	<div class="widgets bg-gray-200 w-1/5 z-10 relative p-5">
		<h3 class="mb-5">WIDGETS</h3>
		<draggable
			:list="widgets"
			:group="{ name: 'widgets', pull: 'clone', put: false }"
			item-key="id"
			class="w-full h-full flex"
		>
			<template #item="{ element }">
				<div class="flex items-center cursor-pointer justify-center h-12 w-12 border shadow-md rounded-md flex-wrap mr-3 bg-white">
					<FeatherIcon :name="element.icon" class="h-6" />
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from 'vuedraggable';
import { ref } from 'vue';

let widgets = ref([{
	id: 1,
	name: 'Container',
	element: "div",
	icon: "square"
}, {
	id: 2,
	name: 'Text',
	element: "span",
	icon: "type"
}, {
	id: 3,
	name: 'Image',
	element: "img",
	icon: "image"
}])

</script>