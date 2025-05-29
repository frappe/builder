import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { CanvasHistory } from "@/types/Builder/BuilderCanvas";
import getBlockTemplate from "@/utils/blockTemplate";
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
) {
	let counter = 0;
	useEventListener(container, "mousedown", (ev: MouseEvent) => {
		if (builderStore.mode === "move") {
			return;
		}
		const initialX = ev.clientX;
		const initialY = ev.clientY;
		if (builderStore.mode === "select") {
			return;
		} else {
			const pauseId = canvasHistory.value?.pause();
			ev.stopPropagation();
			let element = document.elementFromPoint(ev.x, ev.y) as HTMLElement;
			let block = getRootBlock();
			if (element) {
				if (element.dataset.blockId) {
					block = findBlock(element.dataset.blockId) || block;
				}
			}
			let parentBlock = getRootBlock();
			if (element.dataset.blockId) {
				parentBlock = findBlock(element.dataset.blockId) || parentBlock;
				while (parentBlock && !parentBlock.canHaveChildren()) {
					parentBlock = parentBlock.getParentBlock() || getRootBlock();
				}
			}
			const child = getBlockTemplate(builderStore.mode);
			const parentElement = document.body.querySelector(
				`.canvas [data-block-id="${parentBlock.blockId}"]`,
			) as HTMLElement;
			const parentOldPosition = parentBlock.getStyle("position");
			if (parentOldPosition === "static" || parentOldPosition === "inherit" || !parentOldPosition) {
				parentBlock.setBaseStyle("position", "relative");
			}
			const parentElementBounds = parentElement.getBoundingClientRect();
			let x = (ev.x - parentElementBounds.left) / canvasProps.scale;
			let y = (ev.y - parentElementBounds.top) / canvasProps.scale;
			const parentWidth = getNumberFromPx(getComputedStyle(parentElement).width);
			const parentHeight = getNumberFromPx(getComputedStyle(parentElement).height);

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
					let width = (mouseMoveEvent.clientX - initialX) / canvasProps.scale;
					let height = (mouseMoveEvent.clientY - initialY) / canvasProps.scale;
					width = clamp(width, 0, parentWidth);
					height = clamp(height, 0, parentHeight);
					const setFullWidth = width === parentWidth;
					childBlock.setBaseStyle("width", setFullWidth ? "100%" : addPxToNumber(width));
					childBlock.setBaseStyle("height", addPxToNumber(height));
				}
			};
			useEventListener(document, "mousemove", mouseMoveHandler);
			useEventListener(
				document,
				"mouseup",
				() => {
					document.removeEventListener("mousemove", mouseMoveHandler);
					parentBlock.setBaseStyle("position", parentOldPosition || "static");
					childBlock.setBaseStyle("position", "static");
					childBlock.setBaseStyle("top", "auto");
					childBlock.setBaseStyle("left", "auto");
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
						if (getNumberFromPx(childBlock.getStyle("width")) < 100) {
							childBlock.setBaseStyle("width", "100%");
						}
						if (getNumberFromPx(childBlock.getStyle("height")) < 100) {
							childBlock.setBaseStyle("height", "200px");
						}
					}
					pauseId && canvasHistory.value?.resume(pauseId, true);
				},
				{ once: true },
			);
		}
	});

	useEventListener(container, "mousedown", (ev: MouseEvent) => {
		if (builderStore.mode === "move") {
			container.value.style.cursor = "grabbing";
			const initialX = ev.clientX;
			const initialY = ev.clientY;
			const initialTranslateX = canvasProps.translateX;
			const initialTranslateY = canvasProps.translateY;
			const mouseMoveHandler = (mouseMoveEvent: MouseEvent) => {
				mouseMoveEvent.preventDefault();
				const diffX = (mouseMoveEvent.clientX - initialX) / canvasProps.scale;
				const diffY = (mouseMoveEvent.clientY - initialY) / canvasProps.scale;
				canvasProps.translateX = initialTranslateX + diffX;
				canvasProps.translateY = initialTranslateY + diffY;
			};
			useEventListener(document, "mousemove", mouseMoveHandler);
			useEventListener(
				document,
				"mouseup",
				() => {
					document.removeEventListener("mousemove", mouseMoveHandler);
					container.value.style.cursor = "grab";
				},
				{ once: true },
			);
			ev.stopPropagation();
			ev.preventDefault();
		}
	});

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

		switch (ev.key) {
			case "ArrowLeft":
				builderStore.activeLayers?.isExpandedInTree(selectedBlock)
					? builderStore.activeLayers.toggleExpanded(selectedBlock)
					: selectSibling("previous", selectParent);
				break;
			case "ArrowRight":
				selectedBlock.hasChildren() && selectedBlock.isVisible()
					? (builderStore.activeLayers?.toggleExpanded(selectedBlock), selectFirstChild())
					: selectNextSiblingOrParent();
				break;
			case "ArrowUp":
				selectBlock(selectedBlock.getSiblingBlock("previous"))
					? selectLastChildInTree(selectedBlock.getSiblingBlock("previous") as Block)
					: selectParent();
				break;
			case "ArrowDown":
				builderStore.activeLayers?.isExpandedInTree(selectedBlock) &&
				selectedBlock.hasChildren() &&
				selectedBlock.isVisible()
					? selectFirstChild()
					: selectNextSiblingOrParent();
				break;
		}
	});

	useEventListener(container, "mouseover", handleMouseOver);
}

function handleMouseOver(e: MouseEvent) {
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
