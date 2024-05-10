<template>
	<div class="page-builder h-screen flex-col overflow-hidden bg-gray-100 dark:bg-zinc-800">
		<BuilderToolbar class="relative z-30"></BuilderToolbar>
		<div>
			<BuilderLeftPanel
				v-show="store.showLeftPanel"
				class="no-scrollbar absolute bottom-0 left-0 top-[var(--toolbar-height)] z-20 overflow-auto border-r-[1px] bg-white dark:border-gray-800 dark:bg-zinc-900"></BuilderLeftPanel>
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
				class="canvas-container absolute bottom-0 top-[var(--toolbar-height)] flex justify-center overflow-hidden bg-gray-400 p-10 dark:bg-zinc-700">
				<template v-slot:header>
					<div
						class="absolute left-0 right-0 top-0 z-20 flex items-center justify-between bg-white p-2 text-sm text-gray-800 dark:bg-zinc-900 dark:text-zinc-400">
						<div class="flex items-center gap-1 text-xs">
							<a @click="store.editPage(false)" class="cursor-pointer">Page</a>
							<FeatherIcon name="chevron-right" class="h-3 w-3" />
							{{ store.getComponent(store.editingComponent).component_name }}
						</div>
						<Button
							class="text-xs dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700"
							@click="
								() => {
									store.editPage(true);
									clearSelectedComponent();
								}
							">
							Save Component
						</Button>
					</div>
				</template>
			</BuilderCanvas>
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
				class="no-scrollbar absolute bottom-0 right-0 top-[var(--toolbar-height)] z-20 overflow-auto border-l-[1px] bg-white dark:border-gray-800 dark:bg-zinc-900"></BuilderRightPanel>
			<Dialog
				style="z-index: 40"
				v-model="store.showHTMLDialog"
				class="overscroll-none"
				:options="{
					title: 'HTML Code',
					size: '6xl',
				}">
				<template #body-content>
					<CodeEditor
						:modelValue="store.editableBlock?.getInnerHTML()"
						type="HTML"
						height="60vh"
						:showLineNumbers="true"
						@update:modelValue="
							(val) => {
								store.editableBlock?.setInnerHTML(val);
								store.editableBlock = null;
							}
						"
						required />
				</template>
			</Dialog>
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
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import Block, { styleProperty } from "@/utils/block";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import {
	addPxToNumber,
	copyToClipboard,
	detachBlockFromComponent,
	getBlockCopy,
	isCtrlOrCmd,
	isHTMLString,
	isJSONString,
	isTargetEditable,
} from "@/utils/helpers";
import { useActiveElement, useDebounceFn, useEventListener, useMagicKeys } from "@vueuse/core";
import { Dialog } from "frappe-ui";
import { computed, nextTick, onActivated, provide, ref, watch, watchEffect } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";
import CodeEditor from "../components/CodeEditor.vue";

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

provide("pageCanvas", pageCanvas);
provide("componentCanvas", componentCanvas);

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
	if (store.activeCanvas?.selectedBlocks.length) {
		const componentDocuments: BuilderComponent[] = [];
		store.activeCanvas?.selectedBlocks.forEach((block: Block) => {
			const components = block.getUsedComponentNames();
			components.forEach((componentName) => {
				const component = store.getComponent(componentName);
				if (component) {
					componentDocuments.push(component);
				}
			});
		});
		const blocksToCopy = store.activeCanvas?.selectedBlocks.map((block) => {
			if (!Boolean(block.extendedFromComponent) && block.isChildOfComponent) {
				return detachBlockFromComponent(block);
			}
			return block;
		});
		// just copy non components
		const dataToCopy = {
			blocks: blocksToCopy,
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
					imageBlock = parentBlock.addChild(getBlockCopy(getBlockTemplate("image")));
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

		if (store.activeCanvas?.selectedBlocks.length && dataObj.blocks[0].blockId !== "root") {
			let parentBlock = store.activeCanvas.selectedBlocks[0];
			while (parentBlock && !parentBlock.canHaveChildren()) {
				parentBlock = parentBlock.getParentBlock() as Block;
			}
			dataObj.blocks.forEach((block: BlockOptions) => {
				parentBlock.addChild(getBlockCopy(block), null, true);
			});
		} else {
			store.pushBlocks(dataObj.blocks);
		}

		// check if data is from builder and a list of blocks and components
		// if yes then create components and then blocks

		return;
	}

	let text = e.clipboardData?.getData("text/plain") as string;
	if (!text) {
		return;
	}

	if (isHTMLString(text)) {
		e.preventDefault();
		// paste html
		if (blockController.isHTML()) {
			blockController.setInnerHTML(text);
		} else {
			let block = null as unknown as Block | BlockOptions;
			block = getBlockTemplate("html");

			if (text.startsWith("<svg")) {
				const dom = new DOMParser().parseFromString(text, "text/html");
				const svg = dom.body.querySelector("svg") as SVGElement;
				const width = svg.getAttribute("width") || "100";
				const height = svg.getAttribute("height") || "100";
				if (width && block.baseStyles) {
					block.baseStyles.width = addPxToNumber(parseInt(width));
					svg.removeAttribute("width");
				}
				if (height && block.baseStyles) {
					block.baseStyles.height = addPxToNumber(parseInt(height));
					svg.removeAttribute("height");
				}
				text = svg.outerHTML;
			}

			block.innerHTML = text;

			const parentBlock = blockController.getSelectedBlocks()[0];
			if (parentBlock) {
				parentBlock.addChild(block);
			} else {
				store.pushBlocks([block]);
			}
		}
		return;
	}
	// try pasting figma text styles
	if (text.includes(":") && !store.editableBlock) {
		e.preventDefault();
		// strip out all comments: line-height: 115%; /* 12.65px */ -> line-height: 115%;
		const strippedText = text.replace(/\/\*.*?\*\//g, "").replace(/\n/g, "");
		const styleObj = strippedText.split(";").reduce((acc: BlockStyleMap, curr) => {
			const [key, value] = curr.split(":").map((item) => (item ? item.trim() : "")) as [
				styleProperty,
				StyleValue
			];
			if (blockController.isText()) {
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
					if (key === "font-family") {
						acc[key] = (value + "").replace(/['"]+/g, "");
						if (String(value).toLowerCase().includes("inter")) {
							acc["font-family"] = "";
						}
					} else {
						acc[key] = value;
					}
				}
			} else if (["width", "height", "box-shadow", "background", "border-radius"].includes(key)) {
				acc[key] = value;
			}
			return acc;
		}, {});
		Object.entries(styleObj).forEach(([key, value]) => {
			blockController.setBaseStyle(key as styleProperty, value);
		});
		return;
	}

	// if selected block is container, create a new text block inside it and set the text
	if (blockController.isContainer()) {
		e.preventDefault();
		const block = getBlockTemplate("text");
		block.innerHTML = text;
		blockController.getSelectedBlocks()[0].addChild(block);
		return;
	}
});

// TODO: Refactor with useMagicKeys
useEventListener(document, "keydown", (e) => {
	if (isTargetEditable(e)) return;
	if (e.key === "z" && isCtrlOrCmd(e) && !e.shiftKey && store.activeCanvas?.history.canUndo) {
		store.activeCanvas?.history.undo();
		e.preventDefault();
		return;
	}
	if (e.key === "z" && e.shiftKey && isCtrlOrCmd(e) && store.activeCanvas?.history.canRedo) {
		store.activeCanvas?.history.redo();
		e.preventDefault();
		return;
	}

	if (e.key === "0" && isCtrlOrCmd(e)) {
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

	if (e.key === "=" && isCtrlOrCmd(e)) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.zoomIn();
		}
		return;
	}

	if (e.key === "-" && isCtrlOrCmd(e)) {
		e.preventDefault();
		if (pageCanvas.value) {
			pageCanvas.value.zoomOut();
		}
		return;
	}

	if (isCtrlOrCmd(e) || e.shiftKey) {
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

	if (e.key === "h") {
		store.mode = "move";
		return;
	}
});

const activeElement = useActiveElement();
const notUsingInput = computed(
	() => activeElement.value?.tagName !== "INPUT" && activeElement.value?.tagName !== "TEXTAREA"
);

const { space } = useMagicKeys({
	passive: false,
	onEventFired(e) {
		if (e.key === " " && notUsingInput.value && !isTargetEditable(e)) {
			e.preventDefault();
		}
	},
});

watch(space, (value) => {
	if (value && !store.editableBlock) {
		store.mode = "move";
	} else if (store.mode === "move") {
		store.mode = store.lastMode !== "move" ? store.lastMode : "select";
	}
});

useEventListener(document, "keydown", (e) => {
	if (e.key === "\\" && isCtrlOrCmd(e)) {
		e.preventDefault();
		if (e.shiftKey) {
			store.showLeftPanel = !store.showLeftPanel;
		} else {
			store.showRightPanel = !store.showRightPanel;
			store.showLeftPanel = store.showRightPanel;
		}
	}
	// save page or component
	if (e.key === "s" && isCtrlOrCmd(e)) {
		e.preventDefault();
		if (store.editingMode === "component") {
			store.editPage(true);
			clearSelectedComponent();
			e.stopPropagation();
			e.preventDefault();
		}
		return;
	}

	if (e.key === "p" && isCtrlOrCmd(e)) {
		e.preventDefault();
		store.savePage();
		router.push({
			name: "preview",
			params: {
				pageId: store.selectedPage as string,
			},
		});
	}

	if (e.key === "c" && isCtrlOrCmd(e) && e.shiftKey) {
		if (blockController.isBLockSelected() && !blockController.multipleBlocksSelected()) {
			e.preventDefault();
			const block = blockController.getSelectedBlocks()[0];
			store.copiedStyle = {
				blockId: block.blockId,
				style: block.getStylesCopy(),
			};
		}
	}

	if (e.key === "d" && isCtrlOrCmd(e)) {
		if (blockController.isBLockSelected() && !blockController.multipleBlocksSelected()) {
			e.preventDefault();
			const block = blockController.getSelectedBlocks()[0];
			block.duplicateBlock();
		}
	}

	if (isTargetEditable(e)) return;

	if ((e.key === "Backspace" || e.key === "Delete") && blockController.isBLockSelected()) {
		function findBlockAndRemove(blocks: Array<Block>, blockId: string) {
			if (blockId === "root") {
				toast.warning("Warning", {
					description: "Cannot delete root block",
				});

				return false;
			}
			blocks.forEach((block, i) => {
				if (block.blockId === blockId) {
					if (block.isChildOfComponentBlock() && !e.shiftKey) {
						toast.warning("Warning", {
							description: "Cannot delete block inside component",
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
		store.setPage(route.params.pageId as string);
	} else {
		webPages.insert
			.submit({
				page_title: "My Page",
				draft_blocks: [store.getRootBlock()],
			})
			.then((data: BuilderPage) => {
				router.push({ name: "builder", params: { pageId: data.name }, force: true });
				store.setPage(data.name);
			});
	}
});

// on tab activation, reload for latest data
useEventListener(document, "visibilitychange", () => {
	if (document.visibilityState === "visible" && !componentCanvas.value) {
		if (route.params.pageId && route.params.pageId !== "new") {
			store.setPage(route.params.pageId as string, false);
		}
	}
});

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

watch(
	() => store.showHTMLDialog,
	(value) => {
		if (!value) {
			store.editableBlock = null;
		}
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
}

[id^="headlessui-menu-items"] button {
	@apply dark:text-zinc-200;
	@apply dark:hover:bg-zinc-700;
}

[id^="headlessui-menu-items"] button svg {
	@apply dark:text-zinc-200;
}

[data-sonner-toaster] {
	font-family: "InterVar";
}

[data-sonner-toast][data-styled="true"] {
	@apply dark:bg-zinc-900;
	@apply dark:border-zinc-800;
}
</style>
