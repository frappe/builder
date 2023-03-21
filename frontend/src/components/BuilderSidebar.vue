<template>
	<div :style="{
		width: `${store.builderLayout.leftPanelWidth}px`
	}">
		<PanelResizer :width="store.builderLayout.leftPanelWidth" side="right"
			@resize="width => store.builderLayout.leftPanelWidth = width">
		</PanelResizer>
		<div class="flex w-full rounded-md bg-gray-200 dark:bg-zinc-700 p-[2px] text-sm mb-4">
			<button
				class="rounded-md px-3 py-[3px] flex-1"
				@click="store.sidebarActiveTab = 'Pages'"
				:class="{ 'bg-white dark:bg-zinc-800 dark:text-gray-200 shadow-md': store.sidebarActiveTab === 'Pages', 'text-gray-700 dark:text-gray-400': store.sidebarActiveTab !== 'Pages' }">
				Pages
			</button>
			<button
				class="ml-1 rounded-md px-3 py-[3px] flex-1"
				@click="store.sidebarActiveTab = 'Components'"
				:class="{ 'bg-white dark:bg-zinc-800 dark:text-gray-200 shadow-md': store.sidebarActiveTab === 'Components', 'text-gray-700 dark:text-gray-400': store.sidebarActiveTab !== 'Components'}">
				Components
			</button>
			<button
				class="ml-1 rounded-md px-3 py-[3px] flex-1"
				@click="store.sidebarActiveTab = 'Layers'"
				:class="{ 'bg-white dark:bg-zinc-800 dark:text-gray-200 shadow-md': store.sidebarActiveTab === 'Layers', 'text-gray-700 dark:text-gray-400': store.sidebarActiveTab !== 'Layers'}">
				Layers
			</button>
		</div>
		<div class="mb-8" v-if="store.sidebarActiveTab === 'Pages'">
			<h3 class="mb-3 text-xs font-bold uppercase text-gray-600">Pages</h3>
			<div
				v-if="!Object.keys(store.pages).length"
				class="text-sm italic text-gray-600">
				No Saved Pages
			</div>
			<div v-for="(page, i) in store.pages">
				<ul>
					<li class="mb-1 flex items-center rounded-md pl-2 cursor-pointer"
						:class="{ 'bg-gray-200 dark:bg-zinc-800': store.builderState.selectedPage === page.name }"
						@click="setPage(page)">
						<FeatherIcon name="globe" class="w-3 h-3 text-gray-600 dark:text-gray-200"></FeatherIcon>
						<a class="p-1 px-2 text-base flex dark:text-gray-200">
							{{ page.page_name }}
						</a>
					</li>
				</ul>
			</div>
		</div>
		<div v-if="store.sidebarActiveTab === 'Components'">
			<Widgets class="mb-7"></Widgets>
			<Templates class="mb-3"></Templates>
		</div>
		<div v-if="store.sidebarActiveTab === 'Layers'">
			<BlockLayers :blocks="store.builderState.blocks"></BlockLayers>
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
import PanelResizer from "./PanelResizer.vue";


const store = useStore();

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "blocks", "page_name", "route"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 10,
	auto: true,
	onSuccess(data) {
		store.pages = data;
		setPage(store.pages["home"])
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
	store.builderState.selectedPage = e.name;
};
</script>