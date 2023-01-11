<template>
	<div class="widgets bg-gray-200 w-1/5 z-10 relative p-5">
		<h3 class="mb-1 text-gray-600 font-bold text-sm">PAGES</h3>
		<div v-for="page, i in store.pages">
			<ul>
				<li>
					<a @click="set_page(page)" class="hover:underline cursor-pointer text-base">{{ page.route }}</a>
				</li>
			</ul>
		</div>
		<h3 class="mb-3 mt-8 text-gray-600 font-bold text-sm">WIDGETS</h3>
		<draggable
			:list="widgets"
			:group="{ name: 'widgets', pull: 'clone', put: false }"
			item-key="id"
			class="w-full flex flex-wrap"
		>
			<template #item="{ element }">
				<div class="flex items-center cursor-pointer justify-center h-10 w-10 border shadow-sm rounded-md mr-2 last:mr-0 mb-2 bg-white">
					<FeatherIcon :name="element.icon" class="h-5 text-gray-700" />
				</div>
			</template>
		</draggable>
	</div>
</template>
<script setup>
import draggable from 'vuedraggable';
import { ref } from 'vue';
import { useStore } from "../store";
const store = useStore();

let widgets = ref([{
	id: 1,
	name: 'Container',
	element: "div",
	icon: "square",
	attributes: {
		class: "bg-gray-300 h-[300px] w-full"
	}
}, {
	id: 2,
	name: 'Text',
	element: "span",
	icon: "type",
	innerText: "Text",
	attributes: {
		contenteditable: true,
		style: "height: 50px; color: black; background: none; border: none; box-shadow: none; min-width: 50px; width: auto;"
	}
}, {
	id: 3,
	name: 'Image',
	element: "img",
	icon: "image",
	attributes: {
		// src: "https://picsum.photos/500/200"
		src: "https://developers.elementor.com/docs/assets/img/elementor-placeholder-image.png",
		class: "bg-gray-600 h-[300px] w-full"
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