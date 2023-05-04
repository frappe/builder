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
		<div class="flex w-full p-[2px] text-sm border-gray-200 dark:border-zinc-800">
			<button
				v-for="tab of ['Widgets', 'Components', 'Layers']"
				:key="tab"
				class="flex-1 p-2"
				@click="store.sidebarActiveTab = tab"
				:class="{
					'border-b-[1px] border-gray-900 dark:border-zinc-500 dark:text-zinc-300':
						store.sidebarActiveTab === tab,
					'text-gray-700 dark:text-zinc-600': store.sidebarActiveTab !== tab,
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
		<div v-show="store.sidebarActiveTab === 'Widgets'">
			<Widgets class="p-4" />
		</div>
		<div v-show="store.sidebarActiveTab === 'Components'">
			<Components class="p-4" />
		</div>
		<div v-show="store.sidebarActiveTab === 'Layers'">
			<BlockLayers class="p-4" :blocks="store.builderState.blocks" />
		</div>
	</div>
</template>
<script setup lang="ts">
import convertHTMLToBlocks from "@/utils/convertHTMLToBlocks";
import { createListResource, createResource } from "frappe-ui";
import { Ref, ref } from "vue";
import useStore from "../store";
import BlockLayers from "./BlockLayers.vue";
import Components from "./BuilderComponents.vue";
import Widgets from "./BuilderWidgets.vue";
import PanelResizer from "./PanelResizer.vue";

import { useRouter } from "vue-router";

const prompt = ref(null) as unknown as Ref<string>;
const router = useRouter();

const store = useStore();
const generating = ref(false);

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "page_name", "route"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 10,
	auto: true,
	onSuccess(data: PageMap) {
		store.pages = data;
	},
	transform(data: any[]) {
		const pages = {} as PageMap;
		data.forEach((d) => {
			pages[d.name] = d;
		});
		return pages;
	},
});

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

const setPage = (page: Page) => {
	router.replace({
		name: "builder",
		params: {
			pageId: page.name,
		},
	})
}
</script>
