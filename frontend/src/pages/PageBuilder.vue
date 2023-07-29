<template>
	<div class="page-builder h-screen flex-col overflow-hidden bg-gray-100">
		<BuilderToolbar
			class="relative z-30 dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"
			:canvas-props="
				store.editingComponent ? store.componentEditorCanvas : store.blockEditorCanvas
			"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				v-show="store.showPanels"
				class="fixed bottom-0 left-0 top-[var(--toolbar-height)] z-20 overflow-auto border-r-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderLeftPanel>
			<BuilderCanvas
				ref="componentEditor"
				v-if="store.editingComponent"
				:block="store.editingComponent"
				:canvas-props="store.componentEditorCanvas"
				:canvas-styles="{
					width: 'auto',
				}"
				:style="{
					left: `${store.showPanels ? store.builderLayout.leftPanelWidth : 0}px`,
					right: `${store.showPanels ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-200 p-10 dark:bg-zinc-800"></BuilderCanvas>
			<BuilderCanvas
				v-else
				ref="blockEditor"
				:block="store.builderState.blocks[0]"
				:canvas-props="store.blockEditorCanvas"
				:canvas-styles="{
					minHeight: '1600px',
				}"
				:style="{
					left: `${store.showPanels ? store.builderLayout.leftPanelWidth : 0}px`,
					right: `${store.showPanels ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-200 p-10 dark:bg-zinc-800"></BuilderCanvas>
			<BuilderRightPanel
				v-show="store.showPanels"
				class="fixed bottom-0 right-0 top-[var(--toolbar-height)] z-20 overflow-auto border-l-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderRightPanel>
		</div>
	</div>
</template>

<script setup lang="ts">
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import BuilderLeftPanel from "@/components/BuilderLeftPanel.vue";
import BuilderRightPanel from "@/components/BuilderRightPanel.vue";
import BuilderToolbar from "@/components/BuilderToolbar.vue";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import blockController from "@/utils/blockController";
import { isHTMLString } from "@/utils/helpers";
import { nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const store = useStore();

const blockEditor = ref<InstanceType<typeof BuilderCanvas> | null>(null);
const componentEditor = ref<HTMLElement | null>(null);

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

document.addEventListener("keydown", (e) => {
	if (e.key === "\\" && e.metaKey) {
		e.preventDefault();
		store.showPanels = !store.showPanels;
	}
});

// detects if user is pasting HTML on HTML block
document.addEventListener("paste", (e) => {
	if (blockController.isHTML()) {
		e.preventDefault();
		const text = e.clipboardData?.getData("text/plain");
		if (text && isHTMLString(text)) {
			blockController.setInnerHTML(text);
		}
	} else {
		const textJSON = e.clipboardData?.getData("text/plain");
		if (textJSON) {
			const data = JSON.parse(textJSON);
			// check if data is from builder and a list of blocks
			if (Array.isArray(data) && data[0].blockId) {
				if (store.builderState.selectedBlocks.length) {
					data.forEach((block: BlockOptions) => {
						delete block.blockId;
						store.builderState.selectedBlocks[0].addChild(block);
					});
				} else {
					store.pushBlocks(data);
				}
			}
		}
	}
});

onMounted(() => {
	if (route.params.pageId && route.params.pageId !== "new") {
		setPage(route.params.pageId as string);
	} else {
		webPages.insert
			.submit({
				page_title: "My Page",
				blocks: [store.getRootBlock()],
			})
			.then((data: WebPageBeta) => {
				router.push({ name: "builder", params: { pageId: data.name } });
				if (data.blocks) {
					data.blocks = JSON.parse(data.blocks);
				}
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
	webPages.fetchOne.submit(pageName).then((data: WebPageBeta[]) => {
		data[0].blocks = JSON.parse(data[0].blocks);
		store.setPage(data[0]);
		nextTick(() => {
			if (blockEditor.value) {
				blockEditor.value.setScaleAndTranslate();
			}
		});
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
