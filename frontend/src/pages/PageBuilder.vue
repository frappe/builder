<template>
	<div class="page-builder h-screen flex-col overflow-hidden bg-gray-100 dark:bg-zinc-800">
		<BuilderToolbar class="relative z-30"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				v-show="store.showLeftPanel"
				class="absolute bottom-0 left-0 top-[var(--toolbar-height)] z-20 overflow-auto border-r-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderLeftPanel>
			<BuilderCanvas
				ref="componentCanvas"
				v-if="store.editingComponent"
				:block-data="store.getComponentBlock(store.editingComponent)"
				:canvas-styles="{
					width: (store.getComponentBlock(store.editingComponent).getStyle('width') + '').endsWith('px')
						? '!fit-content'
						: null,
					padding: '40px',
				}"
				:style="{
					left: `${store.showLeftPanel ? store.builderLayout.leftPanelWidth : 0}px`,
					right: `${store.showRightPanel ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-400 p-10 dark:bg-zinc-700"></BuilderCanvas>
			<BuilderCanvas
				v-show="!store.editingComponent"
				ref="pageCanvas"
				v-if="store.pageBlocks[0]"
				:block-data="store.pageBlocks[0]"
				:canvas-styles="{
					minHeight: '1000px',
				}"
				:style="{
					left: `${store.showLeftPanel ? store.builderLayout.leftPanelWidth : 0}px`,
					right: `${store.showRightPanel ? store.builderLayout.rightPanelWidth : 0}px`,
				}"
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-200 p-10 dark:bg-zinc-800"></BuilderCanvas>
			<BuilderRightPanel
				v-show="store.showRightPanel"
				class="absolute bottom-0 right-0 top-[var(--toolbar-height)] z-20 overflow-auto border-l-[1px] bg-white no-scrollbar dark:border-gray-800 dark:bg-zinc-900"></BuilderRightPanel>
		</div>
		<PageScript
			v-if="store.selectedPage && store.getActivePage()"
			v-show="showPageScriptPanel"
			:page="store.getActivePage()"></PageScript>
	</div>
</template>

<script setup lang="ts">
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import BuilderLeftPanel from "@/components/BuilderLeftPanel.vue";
import BuilderRightPanel from "@/components/BuilderRightPanel.vue";
import BuilderToolbar from "@/components/BuilderToolbar.vue";
import PageScript from "@/components/PageScript.vue";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import Block, { styleProperty } from "@/utils/block";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import convertHTMLToBlocks from "@/utils/convertHTMLToBlocks";
import { copyToClipboard, isHTMLString, isJSONString, isTargetEditable } from "@/utils/helpers";
import { useDebounceFn, useEventListener, useMagicKeys, whenever } from "@vueuse/core";
import { toast } from "frappe-ui";
import { nextTick, onActivated, provide, ref, watch, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";

const route = useRoute();
const router = useRouter();
const store = useStore();

declare global {
	interface Window {
		store: typeof store;
		blockController: typeof blockController;
	}
}

window.store = store;
window.blockController = blockController;

const pageCanvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);
const componentCanvas = ref<InstanceType<typeof BuilderCanvas> | null>(null);

const showPageScriptPanel = ref(false);
const keys = useMagicKeys();
const CtrlBacktick = keys["Ctrl+`"];

provide("pageCanvas", pageCanvas);
provide("componentCanvas", componentCanvas);

whenever(CtrlBacktick, () => {
	showPageScriptPanel.value = !showPageScriptPanel.value;
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

useEventListener(document, "copy", (e) => {
	if (isTargetEditable(e)) return;
	e.preventDefault();
	if (store.selectedBlocks.length) {
		const componentDocuments: BuilderComponent[] = [];
		store.selectedBlocks.forEach((block: Block) => {
			const components = block.getUsedComponentNames();
			components.forEach((componentName) => {
				const component = store.getComponent(componentName);
				if (component) {
					componentDocuments.push(component);
				}
			});
		});

		const dataToCopy = {
			blocks: store.selectedBlocks,
			components: componentDocuments,
		};
		copyToClipboard(dataToCopy, e, "builder-copied-blocks");
	}
});

useEventListener(document, "paste", async (e) => {
	if (isTargetEditable(e)) return;
	e.stopPropagation();
	const clipboardItems = Array.from(e.clipboardData?.items || []);

	// paste image from clipboard
	if (clipboardItems.some((item) => item.type.includes("image"))) {
		e.preventDefault();
		const file = clipboardItems.find((item) => item.type.includes("image"))?.getAsFile();
		if (file) {
			store.uploadFile(file).then((res: { fileURL: string; fileName: string }) => {
				const selectedBlocks = blockController.getSelectedBlocks();
				const parentBlock = selectedBlocks.length
					? selectedBlocks[0]
					: (store.activeCanvas?.getFirstBlock() as Block);
				let imageBlock = null as unknown as Block;
				if (parentBlock.isImage()) {
					imageBlock = parentBlock;
				} else {
					imageBlock = parentBlock.addChild(store.getBlockCopy(getBlockTemplate("image")));
				}
				imageBlock.setAttribute("src", res.fileURL);
			});
		}
		return;
	}

	const data = e.clipboardData?.getData("builder-copied-blocks") as string;
	// paste blocks directly
	if (data && isJSONString(data)) {
		const dataObj = JSON.parse(data) as { blocks: Block[]; components: BuilderComponent[] };

		for (const component of dataObj.components) {
			delete component.for_web_page;
			await store.createComponent(component, true);
		}

		if (store.selectedBlocks.length && dataObj.blocks[0].blockId !== "root") {
			dataObj.blocks.forEach((block: BlockOptions) => {
				store.selectedBlocks[0].addChild(store.getBlockCopy(block));
			});
		} else {
			store.pushBlocks(dataObj.blocks);
		}

		// check if data is from builder and a list of blocks and components
		// if yes then create components and then blocks

		return;
	}

	const text = e.clipboardData?.getData("text/plain") as string;
	if (!text) {
		return;
	}

	if (isHTMLString(text)) {
		e.preventDefault();
		// paste html
		if (blockController.isHTML()) {
			blockController.setInnerHTML(text);
		} else {
			// create block from html
			const block = convertHTMLToBlocks(text, true) as BlockOptions;
			const parentBlock = blockController.getSelectedBlocks()[0];
			if (!block) return;
			if (parentBlock) {
				parentBlock.addChild(block);
			} else {
				store.pushBlocks([block]);
			}
		}
		return;
	} else {
		// try pasting figma text styles
		if (blockController.isText() && text.includes(":") && !store.editableBlock) {
			e.preventDefault();
			// strip out all comments: line-height: 115%; /* 12.65px */ -> line-height: 115%;
			const strippedText = text.replace(/\/\*.*?\*\//g, "");
			const styleObj = strippedText.split(";").reduce((acc: BlockStyleMap, curr) => {
				const [key, value] = curr.split(":").map((item) => (item ? item.trim() : "")) as [
					styleProperty,
					StyleValue
				];
				if (
					[
						"font-family",
						"font-size",
						"font-weight",
						"line-height",
						"letter-spacing",
						"text-align",
						"text-transform",
						"color",
					].includes(key)
				) {
					acc[key] = value;
					if (key === "font-family" && String(value).toLowerCase().includes("inter")) {
						acc["font-family"] = "";
					}
				}
				return acc;
			}, {});
			Object.entries(styleObj).forEach(([key, value]) => {
				blockController.setBaseStyle(key as styleProperty, value);
			});
		}
		return;
	}
});

// TODO: Refactor with useMagicKeys
useEventListener(document, "keydown", (e) => {
	if (isTargetEditable(e)) return;
	if (e.key === "z" && e.metaKey && !e.shiftKey && store.activeCanvas?.history.canUndo) {
		store.activeCanvas?.history.undo();
		updateSelectedBlocks();
		e.preventDefault();
		return;
	}
	if (e.key === "z" && e.shiftKey && e.metaKey && store.activeCanvas?.history.canRedo) {
		store.activeCanvas?.history.redo();
		updateSelectedBlocks();
		e.preventDefault();
		return;
	}

	if (e.key === "0" && e.metaKey) {
		e.preventDefault();
		if (pageCanvas.value) {
			if (e.shiftKey) {
				pageCanvas.value.setScaleAndTranslate();
			} else {
				pageCanvas.value.resetZoom();
			}
		}
		return;
	}

	if (e.key === "ArrowRight" && !blockController.isBLockSelected()) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.moveCanvas("right");
		}
		return;
	}

	if (e.key === "ArrowLeft" && !blockController.isBLockSelected()) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.moveCanvas("left");
		}
		return;
	}

	if (e.key === "ArrowUp" && !blockController.isBLockSelected()) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.moveCanvas("up");
		}
		return;
	}

	if (e.key === "ArrowDown" && !blockController.isBLockSelected()) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.moveCanvas("down");
		}
		return;
	}

	if (e.key === "=" && e.metaKey) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.zoomIn();
		}
		return;
	}

	if (e.key === "-" && e.metaKey) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.zoomOut();
		}
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
	if (e.key === "\\" && e.metaKey) {
		e.preventDefault();
		if (e.shiftKey) {
			store.showLeftPanel = !store.showLeftPanel;
		} else {
			store.showRightPanel = !store.showRightPanel;
			store.showLeftPanel = store.showRightPanel;
		}
	}
	// save page or component
	if (e.key === "s" && (e.ctrlKey || e.metaKey)) {
		e.preventDefault();
		if (store.editingMode === "component") {
			store.editPage(true);
			clearSelectedComponent();
			e.stopPropagation();
			e.preventDefault();
		}
		return;
	}

	if (e.key === "p" && (e.ctrlKey || e.metaKey)) {
		e.preventDefault();
		store.savePage();
		router.push({
			name: "preview",
			params: {
				pageId: store.selectedPage as string,
			},
		});
	}

	if (e.key === "c" && e.metaKey && e.shiftKey) {
		if (blockController.isBLockSelected() && !blockController.multipleBlocksSelected()) {
			e.preventDefault();
			const block = blockController.getSelectedBlocks()[0];
			store.copiedStyle = {
				blockId: block.blockId,
				style: block.getStylesCopy(),
			};
		}
	}

	if (e.key === "d" && e.metaKey) {
		if (blockController.isBLockSelected() && !blockController.multipleBlocksSelected()) {
			e.preventDefault();
			const block = blockController.getSelectedBlocks()[0];
			block.duplicateBlock();
		}
	}

	if (isTargetEditable(e)) return;

	if (e.key === "Backspace" && blockController.isBLockSelected()) {
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
					if (block.isChildOfComponentBlock() && !e.shiftKey) {
						toast({
							title: "Warning",
							text: "Cannot Delete Block Inside Component",
							icon: "alert-circle",
							iconClasses: "text-yellow-500",
							position: "top-left",
						});
						return false;
					} else {
						blocks.splice(i, 1);
						nextTick(() => {
							// select the next sibling block
							if (blocks.length && blocks[i]) {
								blocks[i].selectBlock();
							}
						});
						return true;
					}
				} else if (block.children) {
					return findBlockAndRemove(block.children, blockId);
				}
			});
		}
		for (const block of blockController.getSelectedBlocks()) {
			findBlockAndRemove([store.activeCanvas?.getFirstBlock() as Block], block.blockId);
		}
		clearSelectedComponent();
		e.stopPropagation();
		return;
	}

	if (e.key === "Escape") {
		store.editPage(false);
		clearSelectedComponent();
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
	store.editableBlock = null;
	if (document.activeElement instanceof HTMLElement) {
		document.activeElement.blur();
	}
};

onActivated(async () => {
	if (route.params.pageId === store.selectedPage) {
		return;
	}
	if (!webPages.data) {
		await webPages.fetchOne.submit(route.params.pageId as string);
	}
	if (route.params.pageId && route.params.pageId !== "new") {
		setPage(route.params.pageId as string);
	} else {
		webPages.insert
			.submit({
				page_title: "My Page",
				draft_blocks: [store.getRootBlock()],
			})
			.then((data: BuilderPage) => {
				router.push({ name: "builder", params: { pageId: data.name }, force: true });
				setPage(data.name);
			});
	}
});

const setPage = (pageName: string) => {
	webPages.fetchOne.submit(pageName).then((data: BuilderPage[]) => {
		store.setPage(data[0]);
		nextTick(() => {
			if (pageCanvas.value) {
				pageCanvas.value.setScaleAndTranslate();
			}
		});
	});
};

// on tab activation, reload for latest data
useEventListener(document, "visibilitychange", () => {
	if (document.visibilityState === "visible") {
		if (route.params.pageId && route.params.pageId !== "new") {
			setPage(route.params.pageId as string);
		}
	}
});

const updateSelectedBlocks = () => {
	const selectedBlocks = blockController.getSelectedBlocks();
	const activeCanvasBlocks = [store.activeCanvas?.block as Block];
	for (const block of selectedBlocks) {
		const blockInActiveCanvas = store.findBlock(block.blockId, activeCanvasBlocks);
		if (blockInActiveCanvas) {
			// replace in place
			selectedBlocks.splice(selectedBlocks.indexOf(block), 1, blockInActiveCanvas);
		}
	}
};

watchEffect(() => {
	if (componentCanvas.value) {
		store.activeCanvas = componentCanvas.value;
	} else {
		store.activeCanvas = pageCanvas.value;
	}
});

const debouncedPageSave = useDebounceFn(store.savePage, 500);

watch(
	() => pageCanvas.value?.block,
	() => {
		if (
			store.selectedPage &&
			!store.settingPage &&
			!store.editingComponent &&
			!pageCanvas.value?.canvasProps?.settingCanvas
		) {
			debouncedPageSave();
		}
	},
	{
		deep: true,
	}
);
</script>

<style>
.page-builder {
	--left-panel-width: 17rem;
	--right-panel-width: 20rem;
	--toolbar-height: 3.5rem;
}

[id^="headlessui-menu-items"] {
	@apply dark:bg-zinc-800;
	@apply no-scrollbar;
	@apply overflow-auto;
	@apply max-h-56;
}

[id^="headlessui-menu-items"] button {
	@apply dark:text-zinc-200;
	@apply dark:hover:bg-zinc-700;
}

[id^="headlessui-menu-items"] button svg {
	@apply dark:text-zinc-200;
}
</style>
