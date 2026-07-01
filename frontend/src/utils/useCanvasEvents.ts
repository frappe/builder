import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { CanvasHistory } from "@/types/Builder/BuilderCanvas";
import getBlockTemplate from "@/utils/blockTemplate";
import { getComputedStyleFor } from "@/utils/canvasFrameDom";
import {
	addPxToNumber,
	getBlock,
	getBlockInfo,
	getNumberFromPx,
	isBlock,
	isTargetEditable,
} from "@/utils/helpers";
import { clamp, useEventListener } from "@vueuse/core";
import { Ref } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

export function useCanvasEvents(
	container: Ref<HTMLElement>,
	canvasProps: CanvasProps,
	canvasHistory: CanvasHistory,
	selectedBlocks: Ref<Block[]>,
	getRootBlock: () => Block,
	findBlock: (blockId: string) => Block | null,
	registerKeyboard = true,
	eventTarget: EventTarget | Ref<EventTarget> = container,
) {
	let counter = 0;
	useEventListener(eventTarget, "mousedown", (ev: MouseEvent) => {
		if (builderStore.mode === "move") {
			return;
		}
		const initialX = ev.clientX;
		const initialY = ev.clientY;
		if (builderStore.mode === "select") {
			return;
		} else {
			if (builderStore.readOnlyMode) return;
			const pauseId = canvasHistory.value?.pause();
			ev.stopPropagation();
			const ownerDocument = container.value.ownerDocument;
			const eventScale = ownerDocument === document ? canvasProps.scale : 1;
			let element = ownerDocument.elementFromPoint(ev.x, ev.y) as HTMLElement;
			let block = getRootBlock();
			if (element) {
				if (element.dataset.blockId) {
					block = findBlock(element.dataset.blockId) || block;
				}
			}
			let parentBlock = getRootBlock();
			if (element?.dataset.blockId) {
				parentBlock = findBlock(element.dataset.blockId) || parentBlock;
				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock() || getRootBlock();
				}
			}
			const child = getBlockTemplate(builderStore.mode);
			const parentElement = ownerDocument.body.querySelector(
				`.canvas [data-block-id="${parentBlock.blockId}"]`,
			) as HTMLElement;
			if (!parentElement) return;
			const parentOldPosition = parentBlock.getStyle("position");
			if (parentOldPosition === "static" || parentOldPosition === "inherit" || !parentOldPosition) {
				parentBlock.setBaseStyle("position", "relative");
			}
			const parentElementBounds = parentElement.getBoundingClientRect();
			let x = (ev.x - parentElementBounds.left) / eventScale;
			let y = (ev.y - parentElementBounds.top) / eventScale;
			const parentWidth = getNumberFromPx(getComputedStyleFor(parentElement).width);
			const parentHeight = getNumberFromPx(getComputedStyleFor(parentElement).height);

			const childBlock = parentBlock.addChild(child);
			childBlock.setBaseStyle("position", "absolute");
			childBlock.setBaseStyle("top", addPxToNumber(y));
			childBlock.setBaseStyle("left", addPxToNumber(x));
			if (builderStore.mode === "container" || builderStore.mode === "repeater") {
				const colors = ["#ededed", "#e2e2e2", "#c7c7c7"];
				childBlock.setBaseStyle("backgroundColor", colors[counter % colors.length]);
				counter++;
			}

			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				if (builderStore.mode === "text") {
					return;
				} else {
					mouseMoveEvent.preventDefault();
					let width = (mouseMoveEvent.clientX - initialX) / eventScale;
					let height = (mouseMoveEvent.clientY - initialY) / eventScale;
					width = clamp(width, 0, parentWidth);
					height = clamp(height, 0, parentHeight);
					const setFullWidth = width === parentWidth;
					childBlock.setBaseStyle("width", setFullWidth ? "100%" : addPxToNumber(width));
					childBlock.setBaseStyle("height", addPxToNumber(height));
				}
			};
			useEventListener(ownerDocument, "mousemove", mouseMoveHandler);
			useEventListener(
				ownerDocument,
				"mouseup",
				() => {
					ownerDocument.removeEventListener("mousemove", mouseMoveHandler);
					parentBlock.setBaseStyle("position", parentOldPosition || "static");
					childBlock.setBaseStyle("position", "static");
					childBlock.setBaseStyle("top", "auto");
					childBlock.setBaseStyle("left", "auto");
					const wasImageMode = builderStore.mode === "image";
					setTimeout(() => {
						builderStore.mode = "select";
					}, 50);
					if (builderStore.mode === "text") {
						pauseId && canvasHistory.value?.resume(pauseId, true);
						canvasStore.editableBlock = childBlock;
						return;
					}
					if (parentBlock.isGrid()) {
						childBlock.setStyle("width", "auto");
						childBlock.setStyle("height", "100%");
					} else {
						if (getNumberFromPx(String(childBlock.getStyle("width") || "")) < 100) {
							childBlock.setBaseStyle("width", "100%");
						}
						if (getNumberFromPx(String(childBlock.getStyle("height") || "")) < 100) {
							childBlock.setBaseStyle("height", "200px");
						}
					}
					pauseId && canvasHistory.value?.resume(pauseId, true);
					if (wasImageMode) {
						builderStore.openImageUpload = true;
					}
				},
				{ once: true },
			);
		}
	});

	useEventListener(eventTarget, "mousedown", (ev: MouseEvent) => {
		if (builderStore.mode === "move") {
			container.value.style.cursor = "grabbing";
			const initialX = ev.clientX;
			const initialY = ev.clientY;
			const initialTranslateX = canvasProps.translateX;
			const initialTranslateY = canvasProps.translateY;
			const ownerDocument = container.value.ownerDocument;
			const eventScale = ownerDocument === document ? canvasProps.scale : 1;
			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				mouseMoveEvent.preventDefault();
				const diffX = (mouseMoveEvent.clientX - initialX) / eventScale;
				const diffY = (mouseMoveEvent.clientY - initialY) / eventScale;
				canvasProps.translateX = initialTranslateX + diffX;
				canvasProps.translateY = initialTranslateY + diffY;
			};
			useEventListener(ownerDocument, "mousemove", mouseMoveHandler);
			useEventListener(
				ownerDocument,
				"mouseup",
				() => {
					ownerDocument.removeEventListener("mousemove", mouseMoveHandler);
					container.value.style.cursor = "grab";
				},
				{ once: true },
			);
			ev.stopPropagation();
			ev.preventDefault();
		}
	});

	if (registerKeyboard)
		useEventListener(document, "keydown", (ev: KeyboardEvent) => {
			// make sure reference container is not hidden or not editable
			if (!container.value.offsetParent || isTargetEditable(ev) || selectedBlocks.value.length !== 1) {
				return;
			}

			const selectedBlock = selectedBlocks.value[0];

			const selectBlock = (block: Block | null) => {
				// TODO: Use canvas's selectBlock instead of canvasStore's to avoid mixup with other canvas
				if (block) canvasStore.selectBlock(block, null, true, true);
				return !!block;
			};

			const selectSibling = (direction: "previous" | "next", fallback: () => void) => {
				selectBlock(selectedBlock.getSiblingBlock(direction)) || fallback();
			};

			const selectParent = () => selectBlock(selectedBlock.getParentBlock());

			const selectFirstChild = () => selectBlock(selectedBlock.children[0]);

			const selectNextSiblingOrParent = () => {
				let sibling = selectedBlock.getSiblingBlock("next");
				let parentBlock = selectedBlock.getParentBlock();
				while (!sibling && parentBlock) {
					sibling = parentBlock.getSiblingBlock("next");
					parentBlock = parentBlock.getParentBlock();
				}
				selectBlock(sibling);
			};

			const selectLastChildInTree = (block: Block) => {
				let currentBlock = block;
				while (builderStore.activeLayers?.isExpandedInTree(currentBlock)) {
					const lastChild = currentBlock.getLastChild() as Block;
					if (!lastChild) break;
					currentBlock = lastChild;
				}
				selectBlock(currentBlock);
			};

			const arrowKeyHandlers = {
				ArrowLeft: () => {
					builderStore.activeLayers?.isExpandedInTree(selectedBlock)
						? builderStore.activeLayers.toggleExpanded(selectedBlock)
						: selectSibling("previous", selectParent);
				},
				ArrowRight: () => {
					selectedBlock.hasChildren() && selectedBlock.isVisible()
						? (builderStore.activeLayers?.toggleExpanded(selectedBlock), selectFirstChild())
						: selectNextSiblingOrParent();
				},
				ArrowUp: () => {
					const previousSibling = selectedBlock.getSiblingBlock("previous");
					previousSibling ? selectLastChildInTree(previousSibling) : selectParent();
				},
				ArrowDown: () => {
					builderStore.activeLayers?.isExpandedInTree(selectedBlock) &&
					selectedBlock.hasChildren() &&
					selectedBlock.isVisible()
						? selectFirstChild()
						: selectNextSiblingOrParent();
				},
			};

			const handler = arrowKeyHandlers[ev.key as keyof typeof arrowKeyHandlers];
			if (handler) {
				handler();
				ev.preventDefault();
			}
		});

	useEventListener(eventTarget, "mouseover", handleMouseOver);
}

function handleMouseOver(e: MouseEvent) {
	if (canvasStore.isMarqueeActive) return;
	if (!isBlock(e)) {
		canvasStore.activeCanvas?.setHoveredBlock(null);
		return;
	}
	if (builderStore.mode === "move" || canvasStore.activeCanvas?.resizingBlock) return;
	const block = getBlock(e);
	const { breakpoint } = getBlockInfo(e);
	canvasStore.activeCanvas?.setHoveredBlock(block?.blockId || null);
	canvasStore.activeCanvas?.setHoveredBreakpoint(breakpoint);
	e.stopPropagation();
}
