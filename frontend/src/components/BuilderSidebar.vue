<template>
	<div
		:style="{
			width: `${store.builderLayout.leftPanelWidth}px`
		}">
		<PanelResizer
			:width="store.builderLayout.leftPanelWidth" side="right"
			@resize="width => store.builderLayout.leftPanelWidth = width" />
		<div class="flex w-full rounded-md bg-gray-200 dark:bg-zinc-700 p-[2px] text-sm mb-4">
			<button
				v-for="tab of ['Pages', 'Components', 'Layers']"
				:key="tab"
				class="rounded-md px-3 py-[3px] flex-1"
				@click="store.sidebarActiveTab = tab"
				:class="{ 'bg-white font-semibold dark:bg-zinc-800 dark:text-gray-200 shadow-md': store.sidebarActiveTab === tab, 'text-gray-700 dark:text-gray-400': store.sidebarActiveTab !== tab }">
				{{ tab }}
			</button>
		</div>
		<div class="mb-8" v-show="store.sidebarActiveTab === 'Pages'">
			<h3 class="mb-3 text-xs font-bold uppercase text-gray-600">
				Pages
			</h3>
			<div
				v-if="!Object.keys(store.pages).length"
				class="text-sm italic text-gray-600">
				No Saved Pages
			</div>
			<div v-for="page of store.pages" :key="page.page_name">
				<ul>
					<li
						class="mb-1 flex items-center rounded-md pl-2 cursor-pointer text-gray-600 dark:text-gray-500 font-medium"
						:class="{ 'bg-gray-200 text-gray-900 dark:text-gray-200 dark:bg-zinc-800': store.builderState.selectedPage === page.name }"
						@click="setPage(page)">
						<FeatherIcon name="globe" class="w-3 h-3" />
						<a class="p-1 px-2 text-base flex">
							{{ page.page_name }}
						</a>
					</li>
				</ul>
			</div>
		</div>
		<div v-show="store.sidebarActiveTab === 'Components'">
			<Widgets class="mb-7" />
			<Templates class="mb-3" />
		</div>
		<div v-show="store.sidebarActiveTab === 'Layers'">
			<BlockLayers :blocks="store.builderState.blocks" />
		</div>
	</div>
</template>
<script setup>
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
		setPage(store.pages[localStorage.getItem("selectedPage") || "home"])
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

const setPage = (page) => {
	if (!page) return
	// clear blocks
	store.clearBlocks();
	store.pushBlocks(page.blocks);
	store.pageName = page.page_name;
	store.route = page.route;
	store.builderState.selectedPage = page.name;
	localStorage.setItem("selectedPage", page.name);
};
</script>