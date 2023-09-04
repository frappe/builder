<template>
	<div class="page-builder h-screen flex-col overflow-hidden bg-gray-100">
		<BuilderToolbar
			class="relative z-30 dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"></BuilderToolbar>
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
					width: (store.getComponentBlock(store.editingComponent).getStyle('width') + '').endsWith('px')
						? '!fit-content'
						: null,
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
import { WebPageComponent } from "@/types/WebsiteBuilder/WebPageComponent";
import Block, { styleProperty } from "@/utils/block";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import convertHTMLToBlocks from "@/utils/convertHTMLToBlocks";
import { copyToClipboard, isHTMLString, isJSONString, isTargetEditable } from "@/utils/helpers";
import { useEventListener, watchDebounced } from "@vueuse/core";
import { toast } from "frappe-ui";
import { nextTick, onActivated, ref } from "vue";
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

const blockEditor = ref<InstanceType<typeof BuilderCanvas> | null>(null);
const componentEditor = ref<HTMLElement | null>(null);

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
		const componentDocuments: WebPageComponent[] = [];
		store.selectedBlocks.forEach((block) => {
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
				const parentBlock = selectedBlocks.length ? selectedBlocks[0] : store.getFirstBlock();
				let imageBlock = null as unknown as Block;
				if (parentBlock.isImage()) {
					imageBlock = parentBlock;
				} else {
					imageBlock = parentBlock.addChild(store.getBlockCopy(getBlockTemplate("image")));
				}
				imageBlock.setAttribute("src", res.fileURL);
				imageBlock.setAttribute("alt", res.fileName);
			});
		}
		return;
	}

	const data = e.clipboardData?.getData("builder-copied-blocks") as string;
	// paste blocks directly
	if (data && isJSONString(data)) {
		const dataObj = JSON.parse(data) as { blocks: Block[]; components: WebPageComponent[] };

		for (const component of dataObj.components) {
			await store.createComponent(component);
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
		if (blockController.isText() && text.includes(":") && !store.builderState.editableBlock) {
			e.preventDefault();
			const styleObj = text.split(";").reduce((acc: BlockStyleMap, curr) => {
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
	if (e.key === "z" && e.metaKey && !e.shiftKey && store.history.canUndo) {
		store.history.undo();
		e.preventDefault();
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
					}
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
			.then((data: WebPageBeta) => {
				router.push({ name: "builder", params: { pageId: data.name }, force: true });
				setPage(data.name);
			});
	}
});

const setPage = (pageName: string) => {
	webPages.fetchOne.submit(pageName).then((data: WebPageBeta[]) => {
		store.setPage(data[0]);
		nextTick(() => {
			if (blockEditor.value) {
				blockEditor.value.setScaleAndTranslate();
			}
		});
	});
};

watchDebounced(
	() => store.builderState.blocks,
	() => {
		if (store.selectedPage && store.autoSave) {
			store.savePage();
		}
	},
	{ debounce: 500, deep: true }
);
</script>

<style>
.page-builder {
	--left-panel-width: 17rem;
	--right-panel-width: 20rem;
	--toolbar-height: 3.5rem;
}
</style>
