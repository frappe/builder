<template>
	<div>
		<h3 class="mb-3 text-gray-600 font-bold text-xs uppercase">WIDGETS</h3>
		<draggable
			:list="widgets"
			:group="{ name: 'blocks', pull: 'clone', put: false }"
			item-key="id"
			class="w-full flex flex-wrap" :clone="handleClone">
			<template #item="{ element }">
				<div
					class="flex items-center cursor-pointer justify-center
					h-10 w-10 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white">
					<FeatherIcon :name="element.icon" class="h-5 text-gray-700" />
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import { ref } from "vue";
import draggable from "vuedraggable";

const handleClone = (item) => {
	const clonedItem = JSON.parse(JSON.stringify(item));
	// set unique id for each cloned item
	clonedItem.id = Math.random().toString(36).substr(2, 9);
	return clonedItem;
};

const widgets = ref([{
	name: "Container",
	element: "section",
	icon: "square",
	blocks: [],
	attributes: {
		class: "w-full h-[300px] bg-blue-100 min-h-fit",
	},
}, {
	name: "Text",
	element: "span",
	icon: "type",
	innerText: "Text",
	attributes: {
		contenteditable: true,
		style: "min-height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto; outline: none; padding: 5px",
	},
}, {
	name: "Spacer",
	element: "div",
	icon: "minus",
	attributes: {
		style: "height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto;",
	},
}, {
	name: "Image",
	element: "img",
	icon: "image",
	attributes: {
		// src: "https://picsum.photos/500/200"
		src: "https://user-images.githubusercontent.com/13928957/212847544-5773795d-2fd6-48d1-8423-b78ecc92522b.png",
		class: "h-[300px] w-full",
	},
	styles: "object-fit: cover",
}]);

</script>

<style>
@tailwind components;

@layer components {
	.Container {
		@apply bg-gray-300;
		@apply h-[300px];
		@apply w-full;
	}

	.Image {
		@apply bg-gray-600;
		@apply h-[300px];
		@apply w-full;
	}
}
</style>
