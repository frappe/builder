<template>
	<h3 class="mb-3 text-gray-600 font-bold text-xs uppercase">WIDGETS</h3>
	<draggable :list="widgets" :group="{ name: 'blocks', pull: 'clone', put: false }" item-key="id"
		class="w-full flex flex-wrap" :clone="handle_clone">
		<template #item="{ element }">
			<div
				class="flex items-center cursor-pointer justify-center h-10 w-10 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white">
				<FeatherIcon :name="element.icon" class="h-5 text-gray-700" />
			</div>
		</template>
	</draggable>
</template>
<script setup>
import draggable from 'vuedraggable';
import { ref } from 'vue';
import { useStore } from "../store";
const store = useStore();

const handle_clone = (item) => {
	let cloned_item = JSON.parse(JSON.stringify(item));
	// set unique id for each cloned item
	cloned_item.id = Math.random().toString(36).substr(2, 9);
	return cloned_item;
}

let widgets = ref([{
	name: 'Container',
	element: "section",
	icon: "square",
	blocks: [],
	attributes: {
		class: "w-full h-[300px] bg-blue-100 min-h-fit"
	}
}, {
	name: 'Text',
	element: "span",
	icon: "type",
	innerText: "Text",
	attributes: {
		contenteditable: true,
		style: "min-height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto; outline: none; padding: 5px"
	}
}, {
	name: 'Spacer',
	element: "div",
	icon: "minus",
	attributes: {
		style: "height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto;"
	}
}, {
	name: 'Image',
	element: "img",
	icon: "image",
	attributes: {
		// src: "https://picsum.photos/500/200"
		src: "https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png",
		class: "h-[300px] w-full"
	},
	styles: "object-fit: cover"
}])

const set_page = (e) => {
	store.blocks.push(...e.options);
	store.page_name = e.page_name;
	store.route = e.route;
}
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