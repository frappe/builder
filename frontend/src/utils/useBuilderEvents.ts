import BuilderCanvas from "@/components/BuilderCanvas.vue";
import webComponent from "@/data/webComponent";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderComponent } from "@/types/Builder/BuilderComponent";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import Block from "@/utils/block";
import blockController from "@/utils/blockController";
import getBlockTemplate from "@/utils/blockTemplate";
import {
	addPxToNumber,
	copyToClipboard,
	detachBlockFromComponent,
	getBlockCopy,
	getCopyWithoutParent,
	isCtrlOrCmd,
	isHTMLString,
	isJSONString,
	isTargetEditable,
	uploadImage,
} from "@/utils/helpers";
import useComponentStore from "@/utils/useComponentStore";
import { useEventListener, useStorage } from "@vueuse/core";
import { Ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { toast } from "vue-sonner";

const store = useStore();
const componentStore = useComponentStore();

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
		if (isTargetEditable(e)) return;
		if (store.activeCanvas?.selectedBlocks.length) {
			e.preventDefault();
			const componentDocuments: BuilderComponent[] = [];
			for (const block of store.activeCanvas?.selectedBlocks) {
				const components = block.getUsedComponentNames();
				for (const componentName of components) {
					const component = componentStore.getComponent(componentName);
					if (component) {
						componentDocuments.push(component);
					}
				}
			}

			const blocksToCopy = store.activeCanvas?.selectedBlocks.map((block) => {
				if (!Boolean(block.extendedFromComponent) && block.isChildOfComponent) {
					return detachBlockFromComponent(block);
				}
				return getCopyWithoutParent(block);
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
				uploadImage(file).then((res: { fileURL: string; fileName: string }) => {
					const selectedBlocks = blockController.getSelectedBlocks();
					const parentBlock = selectedBlocks.length
						? selectedBlocks[0]
						: (store.activeCanvas?.getRootBlock() as Block);
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
				await componentStore.createComponent(component, true);
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
				store.showLeftPanel = !store.showLeftPanel;
			} else {
				store.showRightPanel = !store.showRightPanel;
				store.showLeftPanel = store.showRightPanel;
			}
		}
		// save page or component
		if (e.key === "s" && isCtrlOrCmd(e)) {
			e.preventDefault();
			if (store.editingMode === "fragment") {
				saveAndExitFragmentMode(e);
				e.stopPropagation();
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

		// command + f should focus on search input
		if (e.key === "f" && isCtrlOrCmd(e)) {
			e.preventDefault();
			document.querySelector(".properties-search-input")?.querySelector("input")?.focus();
		}

		if (e.key === "c" && isCtrlOrCmd(e) && e.shiftKey) {
			if (blockController.isBLockSelected() && !blockController.multipleBlocksSelected()) {
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
			if (blockController.isBLockSelected() && !blockController.multipleBlocksSelected()) {
				e.preventDefault();
				const block = blockController.getSelectedBlocks()[0];
				block.duplicateBlock();
			}
		}

		if (isTargetEditable(e)) return;

		if ((e.key === "Backspace" || e.key === "Delete") && blockController.isBLockSelected()) {
			for (const block of blockController.getSelectedBlocks()) {
				store.activeCanvas?.removeBlock(block);
			}
			clearSelection();
			e.stopPropagation();
			return;
		}

		if (e.key === "Escape") {
			store.exitFragmentMode(e);
		}

		// handle arrow keys
		if (e.key.startsWith("Arrow") && blockController.isBLockSelected()) {
			const key = e.key.replace("Arrow", "").toLowerCase() as "up" | "down" | "left" | "right";
			for (const block of blockController.getSelectedBlocks()) {
				block.move(key);
			}
		}
	});

	// TODO: Refactor with useMagicKeys
	useEventListener(document, "keydown", (e) => {
		if (isTargetEditable(e)) return;
		if (e.key === "z" && isCtrlOrCmd(e) && !e.shiftKey && store.activeCanvas?.history?.canUndo) {
			store.activeCanvas?.history.undo();
			e.preventDefault();
			return;
		}
		if (e.key === "z" && e.shiftKey && isCtrlOrCmd(e) && store.activeCanvas?.history?.canRedo) {
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

	// on tab activation, reload for latest data
	useEventListener(document, "visibilitychange", () => {
		if (document.visibilityState === "visible" && !fragmentCanvas.value) {
			if (route.params.pageId && route.params.pageId !== "new") {
				const currentModified = store.activePage?.modified;
				webComponent.reload();
				webPages.fetchOne.submit(store.activePage?.name).then((doc: BuilderPage[]) => {
					if (currentModified !== doc[0]?.modified) {
						store.setPage(route.params.pageId as string, false);
					}
				});
			}
		}
	});
}

const clearSelection = () => {
	blockController.clearSelection();
	store.editableBlock = null;
	if (document.activeElement instanceof HTMLElement) {
		document.activeElement.blur();
	}
};
