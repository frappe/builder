<template>
	<div>
		<div class="flex w-fit rounded-md bg-gray-200 dark:bg-gray-700 p-[2px] text-sm mb-4">
			<button
				class="rounded-md px-3 py-[3px]"
				@click="currentView = 'Pages'"
				:class="{ 'bg-white dark:bg-gray-800 dark:text-gray-200 shadow-md': currentView === 'Pages', 'text-gray-700 dark:text-gray-400': currentView !== 'Pages' }">
				Pages
			</button>
			<button
				class="ml-1 rounded-md px-3 py-[3px]"
				@click="currentView = 'Components'"
				:class="{ 'bg-white dark:bg-gray-800 dark:text-gray-200 shadow-md': currentView === 'Components', 'text-gray-700 dark:text-gray-400': currentView !== 'Components'}">
				Components
			</button>
			<button
				class="ml-1 rounded-md px-3 py-[3px]"
				@click="currentView = 'Layers'"
				:class="{ 'bg-white dark:bg-gray-800 dark:text-gray-200 shadow-md': currentView === 'Layers', 'text-gray-700 dark:text-gray-400': currentView !== 'Layers'}">
				Layers
			</button>
		</div>
		<div class="mb-8" v-if="currentView === 'Pages'">
			<h3 class="mb-3 text-xs font-bold uppercase text-gray-600">Pages</h3>
			<div
				v-if="!Object.keys(store.pages).length"
				class="text-sm italic text-gray-600">
				No Saved Pages
			</div>
			<div v-for="(page, i) in store.pages">
				<ul>
					<li class="mb-1 flex items-center rounded-md pl-2 cursor-pointer"
						:class="{ 'bg-gray-200 dark:bg-gray-700': store.selectedPage === page.name }"
						@click="setPage(page)">
						<FeatherIcon name="globe" class="w-3 h-3 text-gray-600 dark:text-gray-200"></FeatherIcon>
						<a class="p-1 px-2 text-base flex dark:text-gray-200">
							{{ page.page_name }}
						</a>
					</li>
				</ul>
			</div>
		</div>
		<div v-if="currentView === 'Components'">
			<Widgets class="mb-7"></Widgets>
			<Templates class="mb-3"></Templates>
		</div>
		<div v-if="currentView === 'Layers'">
			<BlockLayers :blocks="store.blocks"></BlockLayers>
		</div>
	</div>
</template>
<script setup>
import { ref } from "vue";
import { createListResource } from "frappe-ui";
import useStore from "../store";
import Widgets from "./BuilderWidgets.vue";
import Templates from "./BuilderTemplates.vue";
import BlockLayers from "./BlockLayers.vue";

const currentView = ref("Components");

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
		setPage(store.pages["framework-home-3"])
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
