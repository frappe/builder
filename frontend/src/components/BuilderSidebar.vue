<template>
	<div class="widgets bg-gray-200 w-1/5 relative p-5 z-20">
		<!-- <div class="mb-5">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase">Pages</h3>
			<div v-if="!Object.keys(store.pages).length"
				class="italic text-gray-600  text-sm">
				No Saved Pages
			</div>
			<div v-for="page, i in store.pages">
				<ul>
					<li>
						<a @click="setPage(page)"
							class="hover:underline cursor-pointer text-base">
							{{ page.name }}
						</a>
					</li>
				</ul>
			</div>
		</div> -->
		<Widgets></Widgets>
		<!-- <Templates></Templates> -->
	</div>
</template>
<script setup>
import { createListResource } from "frappe-ui";
import useStore from "../store";
import Widgets from "./BuilderWidgets.vue";

const store = useStore();

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "options", "page_name", "route"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 5,
	auto: true,
	onSuccess(data) {
		store.pages = data;
	},
	transform(data) {
		const pages = {};
		data.forEach((d) => {
			pages[d.name] = d;
			pages[d.name].options = JSON.parse(d.options);
		});
		return pages;
	},
});

const setPage = (e) => {
	// clear blocks
	store.blocks.length = 0;
	store.blocks.push(...e.options);
	store.pageName = e.pageName;
	store.route = e.route;
};

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
