import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { useEventListener } from "@vueuse/core";
import { findNearestSiblingIndex } from "./helpers";
const canvasStore = useCanvasStore();

export function useDraggableBlock(block: Block, target: HTMLElement, options: { ghostScale?: number }) {
	let ghostElement = null as HTMLElement | null;
	const handleDragStart = (e: DragEvent) => {
		e.dataTransfer?.setData("draggingBlockId", block.blockId);
		ghostElement = target.cloneNode(true) as HTMLElement;
		ghostElement.id = "ghost";
		ghostElement.style.position = "fixed";
		ghostElement.style.transform = `scale(${options.ghostScale || 1})`;
		ghostElement.style.pointerEvents = "none";
		ghostElement.style.zIndex = "999999";
		document.body.appendChild(ghostElement);
		if (e.dataTransfer) {
			e.dataTransfer.effectAllowed = "move";
			const blankImage = new Image();
			blankImage.src =
				"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='1' height='1'></svg>";
			e.dataTransfer.setDragImage(blankImage, e.offsetX, e.offsetY);
		}
		e.stopPropagation();
	};

	const handleDrag = (e: DragEvent) => {
		const target = e.target as HTMLElement;
		ghostElement = ghostElement as HTMLElement;
		ghostElement.style.left = e.clientX - target.offsetWidth / 2 + "px";
		ghostElement.style.top = e.clientY - target.offsetHeight / 2 + "px";
		e.stopPropagation();
	};

	const handleDrop = (e: DragEvent) => {
		const pauseId = canvasStore.activeCanvas?.history?.pause();
		// move block to new container
		if (e.dataTransfer) {
			const draggingBlockId = e.dataTransfer.getData("draggingBlockId");
			const draggingBlock = canvasStore.activeCanvas?.findBlock(draggingBlockId) as Block;
			const nearestElementIndex = findNearestSiblingIndex(e);
			if (draggingBlock) {
				const newParent = block;
				const oldParent = draggingBlock.getParentBlock() as Block;
				if (newParent.blockId === oldParent.blockId) {
					newParent.moveChild(draggingBlock, nearestElementIndex);
				} else if (newParent.canHaveChildren() && newParent.isContainer()) {
					if (oldParent) {
						oldParent.removeChild(draggingBlock);
					}
					newParent.addChild(draggingBlock, nearestElementIndex);
					canvasStore.selectBlock(draggingBlock, e);
				}
				e.stopPropagation();
			}
		}
		pauseId && canvasStore.activeCanvas?.history?.resume(pauseId, true);
	};

	const handleDragEnd = (e: DragEvent) => {
		if (ghostElement) {
			ghostElement.remove();
		}
		if (e.dataTransfer && e.dataTransfer.getData("draggingBlockId")) {
			e.dataTransfer.dropEffect = "none";
			e.stopPropagation();
		}
	};

	const handleDragEnter = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
	};

	const handleDragOver = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
	};

	const handleDragLeave = (e: DragEvent) => {
		e.preventDefault();
		e.stopPropagation();
	};

	useEventListener(target, "dragstart", handleDragStart);
	useEventListener(target, "drag", handleDrag);
	useEventListener(target, "drop", handleDrop);
	useEventListener(target, "dragend", handleDragEnd);
	useEventListener(target, "dragenter", handleDragEnter);
	useEventListener(target, "dragover", handleDragOver);
	useEventListener(target, "dragleave", handleDragLeave);
}
