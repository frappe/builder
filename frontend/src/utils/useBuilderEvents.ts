import type Block from "@/block";
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import webComponent from "@/data/webComponent";
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";

import { copyBuilderBlocks, pasteBuilderBlocks } from "@/utils/builderBlockCopyPaste";
import {
	addPxToNumber,
	getBlockCopy,
	isDialogOpen,
	isHTMLString,
	isTargetEditable,
	showDialog,
	triggerCopyEvent,
	uploadBuilderAsset,
} from "@/utils/helpers";
import { useShortcut } from "@/utils/useShortcut";
import { useEventListener, useStorage } from "@vueuse/core";
import { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

const builderStore = useBuilderStore();
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
		if (isTargetEditable(e) || canvasStore.editableBlock || isDialogOpen()) return;
		copySelectedBlocksToClipboard(e);
	});

	useEventListener(document, "cut", (e) => {
		if (isTargetEditable(e) || canvasStore.editableBlock) return;
		if (builderStore.readOnlyMode) return;
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
		if (builderStore.readOnlyMode) return;
		e.stopPropagation();
		const clipboardItems = Array.from(e.clipboardData?.items || []);

		// paste image from clipboard
		if (clipboardItems.some((item) => item.type.includes("image"))) {
			e.preventDefault();
			const file = clipboardItems.find((item) => item.type.includes("image"))?.getAsFile();
			if (file) {
				uploadBuilderAsset(file).then((res: { fileURL: string; fileName: string }) => {
					const selectedBlocks = blockController.getSelectedBlocks();
					let parentBlock = selectedBlocks.length
						? selectedBlocks[0]
						: (canvasStore.activeCanvas?.getRootBlock() as Block);

					let imageBlock = null as unknown as Block;
					if (parentBlock.isImage()) {
						imageBlock = parentBlock;
						imageBlock.setAttribute("src", res.fileURL);
					} else {
						while (parentBlock && !parentBlock.canHaveChildren()) {
							parentBlock = parentBlock.getParentBlock();
						}

						if (parentBlock) {
							imageBlock = parentBlock.addChild(getBlockCopy(getBlockTemplate("image")));
							imageBlock.setAttribute("src", res.fileURL);
						}
					}
				});
			}
			return;
		}

		let text = e.clipboardData?.getData("text/plain") as string || "";

		await pasteBuilderBlocks(e, window.location.origin);

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

				const selectedBlocks = blockController.getSelectedBlocks();
				let parentBlock = selectedBlocks.length ? selectedBlocks[0] : null;

				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock();
				}

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
		if (blockController.canHaveChildren() && blockController.isContainer()) {
			e.preventDefault();
			const block = getBlockTemplate("text");
			block.innerHTML = text;
			blockController.getSelectedBlocks()[0].addChild(block);
			return;
		}
	});

	useShortcut([
		{
			key: "\\",
			ctrl: true,
			description: "Toggle panels",
			group: "View",
			handler: (e) => {
				builderStore.showRightPanel = !builderStore.showRightPanel;
				builderStore.showLeftPanel = builderStore.showRightPanel;
			},
		},
		{
			key: "\\",
			ctrl: true,
			shift: true,
			description: "Toggle left panel",
			group: "View",
			handler: () => {
				builderStore.showLeftPanel = !builderStore.showLeftPanel;
			},
		},
		{
			key: "s",
			ctrl: true,
			description: "Save page / component",
			group: "General",
			allowInInput: true,
			handler: (e) => {
				if (canvasStore.editingMode === "fragment") {
					saveAndExitFragmentMode(e);
					e.stopPropagation();
				}
			},
		},
		{
			key: "p",
			ctrl: true,
			description: "Preview",
			group: "General",
			handler: () => {
				pageStore.savePage();
				router.push({
					name: "preview",
					params: {
						pageId: pageStore.selectedPage as string,
					},
				});
			},
		},
		{
			key: "f",
			ctrl: true,
			shift: true,
			description: "Search blocks",
			group: "General",
			handler: () => {
				builderStore.showSearchBlock = true;
			},
		},
		{
			key: "f",
			ctrl: true,
			description: "Focus property search",
			group: "General",
			handler: () => {
				document.querySelector(".properties-search-input")?.querySelector("input")?.focus();
			},
		},
		{
			key: "c",
			ctrl: true,
			shift: true,
			description: "Copy block styles",
			group: "Edit",
			handler: () => {
				if (blockController.isBlockSelected() && !blockController.multipleBlocksSelected()) {
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
			},
		},
		{
			key: "d",
			ctrl: true,
			description: "Duplicate block",
			group: "Edit",
			handler: () => {
				if (builderStore.readOnlyMode) return;
				if (blockController.isBlockSelected() && !blockController.multipleBlocksSelected()) {
					const block = blockController.getSelectedBlocks()[0];
					block.duplicateBlock();
				}
			},
		},
		{
			key: "Backspace",
			description: "Delete selected blocks",
			group: "Edit",
			handler: (e) => {
				if (builderStore.readOnlyMode) return;
				if (!blockController.isBlockSelected()) return;
				for (const block of blockController.getSelectedBlocks()) {
					canvasStore.activeCanvas?.removeBlock(block, e.shiftKey);
				}
				clearSelection();
				e.stopPropagation();
			},
		},
		{
			key: "Delete",
			description: "Delete selected blocks",
			group: "Edit",
			handler: (e) => {
				if (builderStore.readOnlyMode) return;
				if (!blockController.isBlockSelected()) return;
				for (const block of blockController.getSelectedBlocks()) {
					canvasStore.activeCanvas?.removeBlock(block, e.shiftKey);
				}
				clearSelection();
				e.stopPropagation();
			},
		},
		{
			key: "Escape",
			description: "Exit current mode",
			group: "General",
			condition: () => canvasStore.editingMode !== "page",
			handler: (e) => {
				canvasStore.exitFragmentMode(e);
			},
			preventDefault: false,
		},
		{
			key: "z",
			ctrl: true,
			description: "Undo",
			group: "Edit",
			handler: () => {
				if (canvasStore.activeCanvas?.history?.canUndo) {
					canvasStore.activeCanvas?.history.undo();
				}
			},
		},
		{
			key: "z",
			ctrl: true,
			shift: true,
			description: "Redo",
			group: "Edit",
			handler: () => {
				if (canvasStore.activeCanvas?.history?.canRedo) {
					canvasStore.activeCanvas?.history.redo();
				}
			},
		},
		{
			key: "0",
			ctrl: true,
			description: "Reset canvas zoom",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.setCanvasZoom?.(1, "center");
				}
			},
		},
		{
			key: "0",
			ctrl: true,
			shift: true,
			description: "Fit canvas to screen",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.setScaleAndTranslate();
				}
			},
		},
		{
			key: "ArrowRight",
			description: "Pan canvas right",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("right");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "ArrowLeft",
			description: "Pan canvas left",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("left");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "ArrowUp",
			description: "Pan canvas up",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("up");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "ArrowDown",
			description: "Pan canvas down",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("down");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "=",
			ctrl: true,
			description: "Zoom in",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.zoomIn();
				}
			},
		},
		{
			key: "-",
			ctrl: true,
			description: "Zoom out",
			group: "Canvas",
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.zoomOut();
				}
			},
		},
		{
			key: "c",
			description: "Container mode",
			group: "Tools",
			handler: () => {
				if (builderStore.readOnlyMode) return;
				builderStore.mode = "container";
			},
		},
		{
			key: "i",
			description: "Image mode",
			group: "Tools",
			handler: () => {
				if (builderStore.readOnlyMode) return;
				builderStore.mode = "image";
			},
		},
		{
			key: "t",
			description: "Text mode",
			group: "Tools",
			handler: () => {
				if (builderStore.readOnlyMode) return;
				builderStore.mode = "text";
			},
		},
		{
			key: "v",
			description: "Select mode",
			group: "Tools",
			handler: () => {
				builderStore.mode = "select";
			},
		},
		{
			key: "h",
			description: "Move / hand mode",
			group: "Tools",
			handler: () => {
				builderStore.mode = "move";
			},
		},
	]);

	// on tab activation, reload for latest data
	useEventListener(document, "visibilitychange", () => {
		if (document.visibilityState === "visible" && !fragmentCanvas.value) {
			if (route.params.pageId && route.params.pageId !== "new") {
				const currentModified = pageStore.activePage?.modified;
				webComponent.reload();
				webPages.fetchOne.submit(pageStore.activePage?.name).then((doc: BuilderPage[]) => {
					if (currentModified !== doc[0]?.modified) {
						pageStore.setPage(route.params.pageId as string, false, route.query);
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
