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
				:block="store.getComponentBlock(store.editingComponent)"
				:canvas-props="store.componentEditorCanvas"
				:canvas-styles="{
					width: 'auto',
					padding: '40px',
				}"
				:style="{
					left: `${store.showPanels ? store.builderLayout.leftPanelWidth : 0}px`,
					right: `${store.showPanels ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-400 p-10 dark:bg-zinc-700"></BuilderCanvas>
			<BuilderCanvas
				v-show="!store.editingComponent"
				ref="blockEditor"
				:block="store.builderState.blocks[0]"
				:canvas-props="store.blockEditorCanvas"
				:canvas-styles="{
					minHeight: '1000px',
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
import Block from "@/utils/block";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import convertHTMLToBlocks from "@/utils/convertHTMLToBlocks";
import { copyToClipboard, isHTMLString } from "@/utils/helpers";
import { useEventListener } from "@vueuse/core";
import { toast } from "frappe-ui";
import { nextTick, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const store = useStore();

const blockEditor = ref<InstanceType<typeof BuilderCanvas> | null>(null);
const componentEditor = ref<HTMLElement | null>(null);

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

// to disable page zoom
useEventListener(
	document,
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

useEventListener(document, "paste", (e) => {
	e.stopPropagation();
	const clipboardItems = Array.from(e.clipboardData?.items || []);
	if (clipboardItems.some((item) => item.type.includes("image"))) {
		e.preventDefault();
		const file = clipboardItems.find((item) => item.type.includes("image"))?.getAsFile();
		if (file) {
			store.uploadFile(file).then((res: { fileURL: string; fileName: string }) => {
				let block = null as unknown as Block;
				if (blockController.isImage()) {
					block = blockController.getSelectedBlocks()[0];
				} else {
					block = store.getBlockCopy(getBlockTemplate("image"));
					if (block) {
						store.pushBlocks([block]);
					}
				}
				block.setAttribute("src", res.fileURL);
				block.setAttribute("alt", res.fileName);
			});
		}
	} else if (blockController.isHTML()) {
		e.preventDefault();
		const text = e.clipboardData?.getData("text/plain");
		if (text && isHTMLString(text)) {
			blockController.setInnerHTML(text);
		}
	} else {
		const text = e.clipboardData?.getData("text/plain") as string;
		try {
			const data = JSON.parse(text);
			// check if data is from builder and a list of blocks
			if (Array.isArray(data) && data[0].blockId) {
				if (store.selectedBlocks.length) {
					data.forEach((block: BlockOptions) => {
						store.selectedBlocks[0].addChild(store.getBlockCopy(block));
					});
				} else {
					store.pushBlocks(data);
				}
			}
		} catch (error) {
			if (text && isHTMLString(text)) {
				e.preventDefault();
				const block = convertHTMLToBlocks(text) as BlockOptions;
				if (block) {
					store.pushBlocks([block]);
				}
			}
		}
	}
});

useEventListener(document, "keydown", (e) => {
	const target = e.target as HTMLElement;
	if (target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.getAttribute("contenteditable")) {
		return;
	}
	if (e.key === "z" && e.metaKey && !e.shiftKey && store.history.canUndo) {
		store.history.undo();
		return;
	}
	if (e.key === "z" && e.shiftKey && e.metaKey && store.history.canRedo) {
		store.history.redo();
		return;
	}

	if (e.metaKey || e.ctrlKey || e.shiftKey) {
		return;
	}

	if (e.key === "c") {
		store.mode = "container";
		return;
	}

	if (e.key === "i") {
		store.mode = "image";
		return;
	}

	if (e.key === "t") {
		store.mode = "text";
		return;
	}

	if (e.key === "v") {
		store.mode = "select";
		return;
	}
});

useEventListener(document, "keydown", (e) => {
	const target = e.target as HTMLElement;
	if (e.key === "\\" && e.metaKey) {
		e.preventDefault();
		store.showPanels = !store.showPanels;
	}
	if (e.key === "c" && e.metaKey && e.target === document.body) {
		e.preventDefault();
		if (store.selectedBlocks.length) {
			copyToClipboard(JSON.stringify(store.selectedBlocks));
		}
	}
	if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
		return;
	}

	if (e.key === "Backspace" && blockController.isBLockSelected() && !target.isContentEditable) {
		function findBlockAndRemove(blocks: Array<Block>, blockId: string) {
			if (blockId === "root") {
				toast({
					title: "Warning",
					text: "Cannot Delete Root Block",
					icon: "alert-circle",
					iconClasses: "text-yellow-500",
					position: "top-left",
				});
				return false;
			}
			blocks.forEach((block, i) => {
				if (block.blockId === blockId) {
					store.history.batch(() => {
						blocks.splice(i, 1);
					});
					nextTick(() => {
						// select the next sibling block
						if (blocks.length && blocks[i]) {
							blocks[i].selectBlock();
						}
					});
					return true;
				} else if (block.children) {
					return findBlockAndRemove(block.children, blockId);
				}
			});
		}
		for (const block of blockController.getSelectedBlocks()) {
			findBlockAndRemove([store.getFirstBlock()], block.blockId);
		}
		clearSelectedComponent();
		e.stopPropagation();
		return;
	}

	if (e.key === "Escape") {
		store.editPage(false);
		clearSelectedComponent();
	}

	if (e.key === "s" && (e.ctrlKey || e.metaKey) && store.editingMode === "component") {
		store.editPage(true);
		clearSelectedComponent();
		e.stopPropagation();
		e.preventDefault();
	}

	// handle arrow keys
	if (e.key.startsWith("Arrow") && blockController.isBLockSelected()) {
		const key = e.key.replace("Arrow", "").toLowerCase() as "up" | "down" | "left" | "right";
		for (const block of blockController.getSelectedBlocks()) {
			block.move(key);
		}
	}
});

const clearSelectedComponent = () => {
	blockController.clearSelection();
	store.builderState.editableBlock = null;
	if (document.activeElement instanceof HTMLElement) {
		document.activeElement.blur();
	}
};

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
