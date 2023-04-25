<template>
	<div
		:style="{
			width: `${store.builderLayout.leftPanelWidth}px`,
		}">
		<div v-if="false" class="mb-5 flex flex-col overflow-hidden rounded-lg text-sm">
			<textarea
				class="h-fit resize-none rounded-sm border-0 bg-gray-300 text-sm outline-none no-scrollbar dark:bg-zinc-700 dark:text-white"
				v-model="prompt"
				:disabled="generating" />
			<button
				@click="getPage"
				type="button"
				class="bg-gray-300 p-2 text-gray-800 dark:bg-zinc-700 dark:text-zinc-300"
				:disabled="generating">
				Generate
			</button>
		</div>
		<PanelResizer
			:width="store.builderLayout.leftPanelWidth"
			side="right"
			@resize="(width) => (store.builderLayout.leftPanelWidth = width)" />
		<div class="mb-4 flex w-full rounded-md bg-gray-200 p-[2px] text-sm dark:bg-zinc-700">
			<button
				v-for="tab of ['Pages', 'Components', 'Layers']"
				:key="tab"
				class="flex-1 rounded-md px-3 py-[3px]"
				@click="store.sidebarActiveTab = tab"
				:class="{
					'bg-white font-semibold shadow-md dark:bg-zinc-800 dark:text-gray-200':
						store.sidebarActiveTab === tab,
					'text-gray-700 dark:text-gray-400': store.sidebarActiveTab !== tab,
				}">
				{{ tab }}
			</button>
		</div>
		<div class="mb-8" v-show="store.sidebarActiveTab === 'Pages'">
			<h3 class="mb-3 text-xs font-bold uppercase text-gray-600">Pages</h3>
			<div v-if="!Object.keys(store.pages).length" class="text-sm italic text-gray-600">No Saved Pages</div>
			<div v-for="page of store.pages" :key="page.page_name">
				<ul>
					<li
						class="mb-1 flex cursor-pointer items-center rounded-md pl-2 font-medium text-gray-600 dark:text-gray-500"
						:class="{
							'bg-gray-200 text-gray-900 dark:bg-zinc-800 dark:text-gray-200':
								store.builderState.selectedPage === page.name,
						}"
						@click="setPage(page)">
						<FeatherIcon name="globe" class="h-3 w-3" />
						<a class="flex p-1 px-2 text-base">
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
<script setup lang="ts">
import { createListResource, createResource } from "frappe-ui";
import { ref, Ref } from "vue";
import useStore from "../store";
import Widgets from "./BuilderWidgets.vue";
import Templates from "./BuilderTemplates.vue";
import BlockLayers from "./BlockLayers.vue";
import PanelResizer from "./PanelResizer.vue";
import convertHTMLToBlocks from "@/utils/convertHTMLToBlocks";

const prompt = ref(null) as unknown as Ref<string>;

const store = useStore();
const generating = ref(false);

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "blocks", "page_name", "route"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 10,
	auto: true,
	onSuccess(data: PageMap) {
		store.pages = data;
		setPage(store.pages[localStorage.getItem("selectedPage") || "home"]);
	},
	transform(data: any[]) {
		const pages = {} as PageMap;
		data.forEach((d) => {
			pages[d.name] = d;
			pages[d.name].blocks = JSON.parse(d.blocks);
		});
		return pages;
	},
});

const setPage = (page: Page) => {
	if (!page) return;
	// clear blocks
	store.clearBlocks();
	store.pushBlocks(page.blocks);
	store.pageName = page.page_name;
	store.route = page.route;
	store.builderState.selectedPage = page.name;
	localStorage.setItem("selectedPage", page.name);
};

const getPage = () => {
	generating.value = true;
	createResource({
		url: "website_builder.api.get_blocks",
		onSuccess(html: string) {
			store.clearBlocks();
			const blocks = convertHTMLToBlocks(html);
			store.pushBlocks([blocks]);
			generating.value = false;
		},
	}).submit({
		prompt: prompt.value,
	});
};
</script>
