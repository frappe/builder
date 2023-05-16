<template>
	<div class="page-builder flex-col bg-gray-100">
		<BuilderToolbar
			class="relative z-30 dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				class="fixed left-0 top-[var(--toolbar-height)] bottom-0 z-20 overflow-auto border-r-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderLeftPanel>
			<BuilderCanvas
				class="canvas-container absolute top-[var(--toolbar-height)] bottom-0 flex justify-center overflow-hidden bg-gray-200 p-10 dark:bg-zinc-800"></BuilderCanvas>
			<BuilderRightPanel
				class="fixed right-0 top-[var(--toolbar-height)] bottom-0 z-20 overflow-auto border-l-[1px] bg-white p-4 pr-2 no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderRightPanel>
		</div>
		<div class="fixed bottom-12 text-center z-40 bg-white block left-[50%] translate-x-[-50%] px-3 py-2 rounded-lg text-sm" v-show="store.canvas.scaling">
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
import { createDocumentResource } from "frappe-ui";
import { onMounted, watch } from "vue";
import { useRoute } from "vue-router";

const route = useRoute();
const store = useStore();

// To disable page zooming
// TODO: Move this to a separate file & find better alternative
document.addEventListener('wheel', event => {
	const { ctrlKey } = event
	if (ctrlKey) {
		event.preventDefault();
		return
	}
}, { passive: false })

onMounted(() => {
	if (route.params.pageId && route.params.pageId !== "new") {
		setPage(route.params.pageId as string)
	} else {
		store.clearBlocks();
	}
})

watch(() => route.params.pageId, () => {
	if (route.params.pageId && route.params.pageId !== "new") {
		setPage(route.params.pageId as string)
	}
})

const setPage = (pageName: string) => {
	createDocumentResource({
		method: "GET",
		doctype: "Web Page Beta",
		name: pageName || "home",
		auto: true,
		onSuccess(page: any) {
			page.blocks = JSON.parse(page.blocks);
			store.setPage(page as Page);
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
