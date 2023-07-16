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
		<div class="flex w-full border-gray-200 p-[2px] text-sm dark:border-zinc-800">
			<button
				v-for="tab of ['Layers', 'Components']"
				:key="tab"
				class="mx-3 flex-1 p-2"
				@click.stop="setActiveTab(tab as LeftSidebarTabOption)"
				:class="{
					'border-b-[1px] border-gray-900 dark:border-zinc-500 dark:text-zinc-300':
						store.sidebarActiveTab === tab,
					'text-gray-700 dark:text-zinc-600': store.sidebarActiveTab !== tab,
				}">
				{{ tab }}
			</button>
		</div>
		<div v-if="store.sidebarActiveTab === 'Components'">
			<BuilderComponents class="p-4" />
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
import BuilderComponents from "./BuilderComponents.vue";
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
	});
};

const setActiveTab = (tab: LeftSidebarTabOption) => {
	store.sidebarActiveTab = tab;
};
</script>
