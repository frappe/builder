<template>
	<div class="widgets bg-gray-200 w-1/5 z-10 relative p-5">
		<!-- <h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Pages</h3>
		<div v-for="page, i in store.pages">
			<ul>
				<li>
					<a @click="set_page(page)" class="hover:underline cursor-pointer text-base">{{ page.route }}</a>
				</li>
			</ul>
		</div> -->
		<Widgets></Widgets>
		<!-- <Templates></Templates> -->
	</div>
</template>
<script setup>
import { useStore } from "../store";
import Widgets from "./Widgets.vue";
import Templates from "./Templates.vue";
const store = useStore();


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