<template>
	<div class="widgets bg-gray-200 w-1/5 relative p-5">
		<!-- <div class="mb-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Pages</h3>
			<div v-if="!Object.keys(store.pages).length" class="italic text-gray-600  text-sm">No Saved Pages</div>
			<div v-for="page, i in store.pages">
				<ul>
					<li>
						<a @click="set_page(page)" class="hover:underline cursor-pointer text-base">{{ page.name }}</a>
					</li>
				</ul>
			</div>
		</div> -->
		<Widgets></Widgets>
		<!-- <Templates></Templates> -->
	</div>
</template>
<script setup>
import { useStore } from "../store";
import { createListResource } from "frappe-ui";
import Widgets from "./Widgets.vue";
const store = useStore();

let pages = createListResource({
	doctype: 'Web Page Beta',
	fields: ['name', 'options', 'page_name', 'route'],
	orderBy: 'creation desc',
	start: 0,
	pageLength: 5,
	auto: true,
	onSuccess(data) {
		console.log('data', data);
		store.pages = data;
	},
	transform(data) {
		let pages = {};
		data.map((d) => {
			pages[d.name] = d;
			pages[d.name].options = JSON.parse(d.options);
		});
		return pages;
	},
})

const set_page = (e) => {
	// clear blocks
	store.blocks.length = 0;
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