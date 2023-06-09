<template>
	<div class="page-builder h-screen flex-col overflow-hidden bg-gray-100">
		<BuilderToolbar
			class="relative z-30 dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				class="fixed bottom-0 left-0 top-[var(--toolbar-height)] z-20 overflow-auto border-r-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderLeftPanel>
			<BuilderCanvas
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-200 p-10 dark:bg-zinc-800"></BuilderCanvas>
			<BuilderRightPanel
				class="fixed bottom-0 right-0 top-[var(--toolbar-height)] z-20 overflow-auto border-l-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderRightPanel>
		</div>
		<div
			class="fixed bottom-12 left-[50%] z-40 block translate-x-[-50%] rounded-lg bg-white px-3 py-2 text-center text-sm"
			v-show="store.canvas.scaling">
			{{ Math.round(store.canvas.scale * 100) + "%" }}
		</div>
	</div>
</template>

<script setup lang="ts">
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import BuilderLeftPanel from "@/components/BuilderLeftPanel.vue";
import BuilderRightPanel from "@/components/BuilderRightPanel.vue";
import BuilderToolbar from "@/components/BuilderToolbar.vue";
import useStore from "@/store";
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { createDocumentResource, createResource } from "frappe-ui";
import { onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const store = useStore();

// To disable page zooming
// TODO: Move this to a separate file & find better alternative
document.addEventListener(
	"wheel",
	(event) => {
		const { ctrlKey } = event;
		if (ctrlKey) {
			event.preventDefault();
			return;
		}
	},
	{ passive: false }
);

onMounted(() => {
	if (route.params.pageId && route.params.pageId !== "new") {
		console.log(route.params.pageId);
		setPage(route.params.pageId as string);
	} else {
		const createPageResource = createResource({
			url: "website_builder.api.create_new_page",
			method: "POST",
			onSuccess(page: any) {
				page.blocks = JSON.parse(page.blocks);
				store.pages[page.name] = page as WebPageBeta;
				store.pageName = page.page_name;
				router.push({ name: "builder", params: { pageId: page.name } });
			},
		});
		createPageResource.submit({
			blocks: [store.getRootBlock()],
		});
	}
});

watch(
	() => route.params.pageId,
	() => {
		if (route.params.pageId && route.params.pageId !== "new") {
			setPage(route.params.pageId as string);
		}
	}
);

const setPage = (pageName: string) => {
	createDocumentResource({
		method: "GET",
		doctype: "Web Page Beta",
		name: pageName || "home",
		auto: true,
		onSuccess(page: any) {
			page.blocks = JSON.parse(page.blocks);
			store.setPage(page as WebPageBeta);
		},
	});
};
</script>

<style>
.page-builder {
	--left-panel-width: 17rem;
	--right-panel-width: 20rem;
	--toolbar-height: 3.5rem;
}
</style>
