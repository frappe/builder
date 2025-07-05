import type Block from "@/block";
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import webComponent from "@/data/webComponent";
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import useComponentStore from "@/stores/componentStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";

import { copyBuilderBlocks, pasteBuilderBlocks } from "@/utils/builderBlockCopyPaste";
import {
	addPxToNumber,
	getBlockCopy,
	isCtrlOrCmd,
	isHTMLString,
	isTargetEditable,
	showDialog,
	triggerCopyEvent,
	uploadImage,
} from "@/utils/helpers";
import { useEventListener, useStorage } from "@vueuse/core";
import { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

const builderStore = useBuilderStore();
const componentStore = useComponentStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

export function useBuilderEvents(
	pageCanvas: Ref<InstanceType<typeof BuilderCanvas> | null>,
	fragmentCanvas: Ref<InstanceType<typeof BuilderCanvas> | null>,
	saveAndExitFragmentMode: (e: KeyboardEvent) => void,
	route: ReturnType<typeof useRoute>,
	router: ReturnType<typeof useRouter>,
) {
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
		{ passive: false },
	);

	useEventListener(document, "copy", (e) => {
		copySelectedBlocksToClipboard(e);
	});

	useEventListener(document, "cut", (e) => {
		if (isTargetEditable(e)) return;
		copySelectedBlocksToClipboard(e);
		if (canvasStore.activeCanvas?.selectedBlocks.length) {
			for (const block of canvasStore.activeCanvas?.selectedBlocks) {
				canvasStore.activeCanvas?.removeBlock(block, true);
			}
			clearSelection();
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
				uploadImage(file).then((res: { fileURL: string; fileName: string }) => {
					const selectedBlocks = blockController.getSelectedBlocks();
					const parentBlock = selectedBlocks.length
						? selectedBlocks[0]
						: (canvasStore.activeCanvas?.getRootBlock() as Block);
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

		await pasteBuilderBlocks(e, window.location.origin);

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
					if (text.includes("<image")) {
						toast.warning("Warning", {
							description: "SVG with inlined image in it is not supported. Please paste it as PNG instead.",
						});
						return;
					}
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
					canvasStore.pushBlocks([block]);
				}
			}
			return;
		}
		// try pasting figma text styles
		if (text.includes(":") && !canvasStore.editableBlock) {
			e.preventDefault();
			// strip out all comments: line-height: 115%; /* 12.65px */ -> line-height: 115%;
			const strippedText = text.replace(/\/\*.*?\*\//g, "").replace(/\n/g, "");
			const styleObj = strippedText.split(";").reduce((acc: BlockStyleMap, curr) => {
				const [key, value] = curr.split(":").map((item) => (item ? item.trim() : "")) as [
					styleProperty,
					StyleValue,
				];
				if (blockController.isText() && !blockController.isLink()) {
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
						].includes(key as string)
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
				} else if (["width", "height", "box-shadow", "background", "border-radius"].includes(key as string)) {
					acc[key] = value;
				}
				return acc;
			}, {});
			Object.entries(styleObj).forEach(([key, value]) => {
				blockController.setStyle(key, value);
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

	useEventListener(document, "keydown", (e) => {
		if (e.key === "\\" && isCtrlOrCmd(e)) {
			e.preventDefault();
			if (e.shiftKey) {
				builderStore.showLeftPanel = !builderStore.showLeftPanel;
			} else {
				builderStore.showRightPanel = !builderStore.showRightPanel;
				builderStore.showLeftPanel = builderStore.showRightPanel;
			}
		}
		// save page or component
		if (e.key === "s" && isCtrlOrCmd(e)) {
			e.preventDefault();
			if (canvasStore.editingMode === "fragment") {
				saveAndExitFragmentMode(e);
				e.stopPropagation();
			}
			return;
		}

		if (e.key === "p" && isCtrlOrCmd(e)) {
			e.preventDefault();
			pageStore.savePage();
			router.push({
				name: "preview",
				params: {
					pageId: pageStore.selectedPage as string,
				},
			});
		}

		// command + f should focus on search input
		if (e.key === "f" && isCtrlOrCmd(e)) {
			e.preventDefault();
			document.querySelector(".properties-search-input")?.querySelector("input")?.focus();
		}

		if (e.key === "f" && isCtrlOrCmd(e) && e.shiftKey) {
			e.preventDefault();
			builderStore.showSearchBlock = true;
		}

		if (e.key === "c" && isCtrlOrCmd(e) && e.shiftKey) {
			if (blockController.isBlockSelected() && !blockController.multipleBlocksSelected()) {
				e.preventDefault();
				const block = blockController.getSelectedBlocks()[0];
				const copiedStyle = useStorage(
					"copiedStyle",
					{ blockId: "", style: {} },
					sessionStorage,
				) as Ref<StyleCopy>;
				copiedStyle.value = {
					blockId: block.blockId,
					style: block.getStylesCopy(),
				};
			}
		}

		if (e.key === "d" && isCtrlOrCmd(e)) {
			if (blockController.isBlockSelected() && !blockController.multipleBlocksSelected()) {
				e.preventDefault();
				const block = blockController.getSelectedBlocks()[0];
				block.duplicateBlock();
			}
		}

		if (isTargetEditable(e)) return;

		if ((e.key === "Backspace" || e.key === "Delete") && blockController.isBlockSelected()) {
			for (const block of blockController.getSelectedBlocks()) {
				canvasStore.activeCanvas?.removeBlock(block, e.shiftKey);
			}
			clearSelection();
			e.stopPropagation();
			return;
		}

		if (e.key === "Escape") {
			canvasStore.exitFragmentMode(e);
		}

		// handle arrow keys
		if (e.key.startsWith("Arrow") && blockController.isBlockSelected()) {
			const key = e.key.replace("Arrow", "").toLowerCase() as "up" | "down" | "left" | "right";
			for (const block of blockController.getSelectedBlocks()) {
				block.move(key);
			}
		}
	});

	// TODO: Refactor with useMagicKeys
	useEventListener(document, "keydown", (e) => {
		if (isTargetEditable(e)) return;
		if (e.key === "z" && isCtrlOrCmd(e) && !e.shiftKey && canvasStore.activeCanvas?.history?.canUndo) {
			canvasStore.activeCanvas?.history.undo();
			e.preventDefault();
			return;
		}
		if (e.key === "z" && e.shiftKey && isCtrlOrCmd(e) && canvasStore.activeCanvas?.history?.canRedo) {
			canvasStore.activeCanvas?.history.redo();
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

		if (e.key === "ArrowRight" && !blockController.isBlockSelected()) {
			e.preventDefault();
			if (pageCanvas.value) {
				pageCanvas.value.moveCanvas("right");
			}
			return;
		}

		if (e.key === "ArrowLeft" && !blockController.isBlockSelected()) {
			e.preventDefault();
			if (pageCanvas.value) {
				pageCanvas.value.moveCanvas("left");
			}
			return;
		}

		if (e.key === "ArrowUp" && !blockController.isBlockSelected()) {
			e.preventDefault();
			if (pageCanvas.value) {
				pageCanvas.value.moveCanvas("up");
			}
			return;
		}

		if (e.key === "ArrowDown" && !blockController.isBlockSelected()) {
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
			builderStore.mode = "container";
			return;
		}

		if (e.key === "i") {
			builderStore.mode = "image";
			return;
		}

		if (e.key === "t") {
			builderStore.mode = "text";
			return;
		}

		if (e.key === "v") {
			builderStore.mode = "select";
			return;
		}

		if (e.key === "h") {
			builderStore.mode = "move";
			return;
		}
	});

	// on tab activation, reload for latest data
	useEventListener(document, "visibilitychange", () => {
		if (document.visibilityState === "visible" && !fragmentCanvas.value) {
			if (route.params.pageId && route.params.pageId !== "new") {
				const currentModified = pageStore.activePage?.modified;
				webComponent.reload();
				webPages.fetchOne.submit(pageStore.activePage?.name).then((doc: BuilderPage[]) => {
					if (currentModified !== doc[0]?.modified) {
						pageStore.setPage(route.params.pageId as string, false);
					}
				});
			}
		}
	});

	// context menu
	useEventListener(document, "contextmenu", async (e) => {
		if (isTargetEditable(e)) return;
		const target =
			<HTMLElement | null>(e.target as HTMLElement)?.closest("[data-block-layer-id]") ||
			(e.target as HTMLElement)?.closest("[data-block-id]");
		if (target) {
			const blockId = target.dataset.blockLayerId || target.dataset.blockId;
			const block = canvasStore.activeCanvas?.findBlock(blockId as string);
			if (block) {
				canvasStore.activeCanvas?.selectBlock(block, blockController.multipleBlocksSelected());
				builderStore.blockContextMenu?.showContextMenu(e, block);
			}
		}
	});
}

const clearSelection = () => {
	blockController.clearSelection();
	canvasStore.editableBlock = null;
	if (document.activeElement instanceof HTMLElement) {
		document.activeElement.blur();
	}
};

const copySelectedBlocksToClipboard = (e: ClipboardEvent) => {
	if (isTargetEditable(e)) return;
	if (
		canvasStore.activeCanvas?.selectedBlocks.length === 1 &&
		canvasStore.activeCanvas.selectedBlocks[0].isRoot() &&
		canvasStore.requiresConfirmationForCopyingEntirePage
	) {
		// Handle dialog first and wait for response
		showDialog({
			title: "Copy entire page?",
			message: "Do you want to copy the entire page including settings and scripts?",
			actions: [
				{
					label: "Yes",
					variant: "solid",
					onClick: () => {
						canvasStore.requiresConfirmationForCopyingEntirePage = false;
						canvasStore.copyEntirePage = true;
						triggerCopyEvent();
					},
				},
				{
					label: "No, just blocks",
					variant: "subtle",
					onClick: () => {
						canvasStore.requiresConfirmationForCopyingEntirePage = false;
						canvasStore.copyEntirePage = false;
						triggerCopyEvent();
					},
				},
			],
			size: "md",
		});
	} else {
		copyBuilderBlocks(e, window.location.origin, canvasStore.copyEntirePage);
		canvasStore.requiresConfirmationForCopyingEntirePage = true;
	}
};
