import type Block from "@/block";
import BuilderCanvas from "@/components/BuilderCanvas.vue";
import webComponent from "@/data/webComponent";
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";

import { copyBuilderBlocks, pasteBuilderBlocks } from "@/utils/builderBlockCopyPaste";
import {
	addPxToNumber,
	getBlockCopy,
	getImageBlock,
	isDialogOpen,
	isHTMLString,
	isOversizedSVG,
	isTargetEditable,
	showDialog,
	triggerCopyEvent,
	uploadBuilderAsset,
	uploadSVGAsFile,
} from "@/utils/helpers";
import { promptOversizedSVG } from "@/utils/dialogs";
import { useEventListener } from "@vueuse/core";
import { commandShortcuts } from "@/components/Commands";
import { toast, useShortcut } from "frappe-ui";
import { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { __ } from "@/translation";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();

async function resolveOversizedSVG(svg: string) {
	if (!isOversizedSVG(svg) || !(await promptOversizedSVG(svg.length))) return null;
	const { fileURL } = await uploadSVGAsFile(svg);
	return fileURL || null;
}

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
		if (isTargetEditable(e) || canvasStore.editableBlock) return;
		if (isDialogOpen() && canvasStore.requiresConfirmationForCopyingEntirePage) return;
		if (window.getSelection()?.toString()) return;
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

		let text = (e.clipboardData?.getData("text/plain") as string) || "";

		await pasteBuilderBlocks(e, window.location.origin);

		if (!text) {
			return;
		}

		if (isHTMLString(text)) {
			e.preventDefault();
			// paste html
			if (blockController.isHTML()) {
				const fileURL = text.startsWith("<svg") ? await resolveOversizedSVG(text) : null;
				blockController.setInnerHTML(fileURL ? `<img src="${fileURL}" />` : text);
			} else {
				let block = null as unknown as Block | BlockOptions;
				block = getBlockTemplate("html");

				if (text.startsWith("<svg")) {
					if (text.includes("<image")) {
						toast.warning(__("Warning"), {
							description: __(
								"SVG with inlined image in it is not supported. Please paste it as PNG instead.",
							),
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

					const fileURL = await resolveOversizedSVG(text);
					if (fileURL) {
						const imageBlock = getImageBlock(fileURL);
						// the image template defaults to cover, which would crop the artwork
						imageBlock.baseStyles = {
							...block.baseStyles,
							...imageBlock.baseStyles,
							objectFit: "contain",
						};
						block = imageBlock;
					}
				}

				if (!block.attributes?.src) {
					block.innerHTML = text;
				}

				const selectedBlocks = blockController.getSelectedBlocks();
				let parentBlock = selectedBlocks.length ? selectedBlocks[0] : null;

				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock();
				}

				if (parentBlock) {
					parentBlock.addChild(block);
				} else {
					canvasStore.pushBlocks([block], false);
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

	// a command that declares keys owns its binding; what is left needs the
	// keyboard event or a canvas ref, so it stays a plain shortcut
	useShortcut([
		...commandShortcuts(),
		{
			key: "s",
			ctrl: true,
			description: __("Save page / component"),
			group: __("General"),
			allowInInput: true,
			handler: (e) => {
				if (canvasStore.editingMode === "fragment") {
					saveAndExitFragmentMode(e);
					e.stopPropagation();
				}
			},
		},
		{
			key: "Backspace",
			description: __("Delete selected blocks"),
			group: __("Edit"),
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
			description: __("Delete selected blocks"),
			group: __("Edit"),
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
			description: __("Exit current mode"),
			group: __("General"),
			condition: () => canvasStore.editingMode !== "page",
			handler: (e) => {
				canvasStore.exitFragmentMode(e);
			},
			preventDefault: false,
		},
		{
			key: "0",
			ctrl: true,
			description: __("Reset canvas zoom"),
			group: __("Canvas"),
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
			description: __("Fit canvas to screen"),
			group: __("Canvas"),
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.setScaleAndTranslate();
				}
			},
		},
		{
			key: "ArrowRight",
			description: __("Pan canvas right"),
			group: __("Canvas"),
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("right");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "ArrowLeft",
			description: __("Pan canvas left"),
			group: __("Canvas"),
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("left");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "ArrowUp",
			description: __("Pan canvas up"),
			group: __("Canvas"),
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.moveCanvas("up");
				}
			},
			condition: () => !blockController.isBlockSelected(),
		},
		{
			key: "ArrowDown",
			description: __("Pan canvas down"),
			group: __("Canvas"),
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
			description: __("Zoom in"),
			group: __("Canvas"),
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.zoomIn();
				}
			},
		},
		{
			key: "-",
			ctrl: true,
			description: __("Zoom out"),
			group: __("Canvas"),
			handler: () => {
				if (pageCanvas.value) {
					pageCanvas.value.zoomOut();
				}
			},
		},
		{
			key: "c",
			description: __("Container mode"),
			group: __("Tools"),
			handler: () => {
				if (builderStore.readOnlyMode) return;
				builderStore.mode = "container";
			},
		},
		{
			key: "i",
			description: __("Image mode"),
			group: __("Tools"),
			handler: () => {
				if (builderStore.readOnlyMode) return;
				builderStore.mode = "image";
			},
		},
		{
			key: "t",
			description: __("Text mode"),
			group: __("Tools"),
			handler: () => {
				if (builderStore.readOnlyMode) return;
				builderStore.mode = "text";
			},
		},
		{
			key: "v",
			description: __("Select mode"),
			group: __("Tools"),
			handler: () => {
				builderStore.mode = "select";
			},
		},
		{
			key: "h",
			description: __("Move / hand mode"),
			group: __("Tools"),
			handler: () => {
				builderStore.mode = "move";
			},
		},
		{
			key: "l",
			ctrl: true,
			shift: true,
			triggeredOn: "hold",
			description: __("Highlight Blocks with Client Scripts"),
			group: __("View"),
			onHold: () => {
				builderStore.highlightBlocksWithClientScripts = true;
			},
			onRelease: () => {
				builderStore.highlightBlocksWithClientScripts = false;
			},
		},
	]);

	// on tab activation, reload for latest data
	useEventListener(document, "visibilitychange", () => {
		if (document.visibilityState === "visible" && !fragmentCanvas.value) {
			if (route.params.pageId && route.params.pageId !== "new") {
				const currentModified = pageStore.activePage?.modified;
				webComponent.reload();
				webPages.fetchOne.submit(pageStore.activePage?.name).then((doc: BuilderPage[] | null) => {
					if (currentModified !== doc?.[0]?.modified) {
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
			title: __("Copy entire page?"),
			message: __("Do you want to copy the entire page including settings and scripts?"),
			actions: [
				{
					label: __("No, just blocks"),
					variant: "subtle",
					onClick: () => {
						canvasStore.requiresConfirmationForCopyingEntirePage = false;
						canvasStore.copyEntirePage = false;
						triggerCopyEvent();
					},
				},
				{
					label: __("Yes"),
					variant: "solid",
					onClick: () => {
						canvasStore.requiresConfirmationForCopyingEntirePage = false;
						canvasStore.copyEntirePage = true;
						triggerCopyEvent();
					},
				},
			],
			size: "md",
		});
	} else {
		copyBuilderBlocks(e, window.location.origin, canvasStore.copyEntirePage);
		canvasStore.requiresConfirmationForCopyingEntirePage = true;
		canvasStore.copyEntirePage = false;
	}
};
