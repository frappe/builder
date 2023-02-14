<template>
	<div>
		<div class="mb-8">
			<h3 class="mb-1 text-gray-600 font-bold text-xs uppercase mb-3">Pages</h3>
			<div v-if="!Object.keys(store.pages).length"
				class="italic text-gray-600  text-sm">
				No Saved Pages
			</div>
			<div v-for="page, i in store.pages">
				<ul>
					<li class="mb-1">
						<a @click="setPage(page)"
							class="cursor-pointer text-base rounded-md p-2" :class="{'bg-gray-200': store.selectedPage === page.name}">
							{{ page.page_name }}
						</a>
					</li>
				</ul>
			</div>
		</div>
		<Widgets class="mb-7"></Widgets>
		<Templates class="mb-3"></Templates>
	</div>
</template>
<script setup>
import { createListResource } from "frappe-ui";
import useStore from "../store";
import Widgets from "./BuilderWidgets.vue";
import Templates from "./BuilderTemplates.vue";

const store = useStore();

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "blocks", "page_name", "route"],
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
			pages[d.name].blocks = JSON.parse(d.blocks);
		});
		return pages;
	},
});

const setPage = (e) => {
	// clear blocks
	store.clearBlocks();
	store.pushBlocks(e.blocks);
	store.pageName = e.page_name;
	store.route = e.route;
	store.selectedPage = e.name;
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
