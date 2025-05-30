import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { CanvasProps } from "@/types/Builder/BuilderCanvas";
import { getRootBlockTemplate } from "@/utils/helpers";
import { useCanvasHistory } from "@/utils/useCanvasHistory";
import { useElementBounding } from "@vueuse/core";
import { nextTick, reactive, ref, Ref } from "vue";
import { toast } from "vue-sonner";

const canvasStore = useCanvasStore();

export function useCanvasUtils(
	canvasProps: CanvasProps,
	canvasContainer: Ref<HTMLElement | null>,
	canvas: Ref<HTMLElement | null>,
	rootBlock: Ref<Block>,
	selectedBlockIds: Ref<Set<string>>,
	canvasHistory: Ref<null | any>,
) {
	const isDirty = ref(false);
	const containerBound = reactive(useElementBounding(canvasContainer));
	const canvasBound = reactive(useElementBounding(canvas));
	async function scrollIntoView(
		blockToFocus: Block,
		canvasProps: CanvasProps,
		canvasContainer: Ref<HTMLElement>,
		canvas: Ref<HTMLElement>,
	) {
		// wait for editor to render
		await new Promise((resolve) => setTimeout(resolve, 100));
		if (!selectedBlockIds.value.has(blockToFocus.blockId)) {
			selectBlock(blockToFocus);
		}
		await nextTick();
		if (
			!canvasContainer.value ||
			!canvas.value ||
			blockToFocus.isRoot() ||
			!blockToFocus.isVisible() ||
			blockToFocus.getParentBlock()?.isSVG()
		) {
			return;
		}
		const container = canvasContainer.value as HTMLElement;
		const containerRect = container.getBoundingClientRect();
		await nextTick();
		const selectedBlock = canvasContainer.value.querySelector(
			`.editor[data-block-id="${blockToFocus.blockId}"][selected=true]`,
		) as HTMLElement;
		if (!selectedBlock) {
			return;
		}
		const blockRect = reactive(useElementBounding(selectedBlock));
		// check if block is in view
		if (
			blockRect.top >= containerRect.top &&
			blockRect.bottom <= containerRect.bottom &&
			blockRect.left >= containerRect.left &&
			blockRect.right <= containerRect.right
		) {
			return;
		}

		let padding = 80;
		let paddingBottom = 200;
		const blockWidth = blockRect.width + padding * 2;
		const containerBound = container.getBoundingClientRect();
		const blockHeight = blockRect.height + padding + paddingBottom;

		const scaleX = containerBound.width / blockWidth;
		const scaleY = containerBound.height / blockHeight;
		const newScale = Math.min(scaleX, scaleY);

		const scaleDiff = canvasProps.scale - canvasProps.scale * newScale;
		if (scaleDiff > 0.2) {
			return;
		}

		if (newScale < 1) {
			canvasProps.scale = canvasProps.scale * newScale;
			await new Promise((resolve) => setTimeout(resolve, 100));
			await nextTick();
			blockRect.update();
		}

		padding = padding * canvasProps.scale;
		paddingBottom = paddingBottom * canvasProps.scale;

		// slide in block from the closest edge of the container
		const diffTop = containerRect.top - blockRect.top + padding;
		const diffBottom = blockRect.bottom - containerRect.bottom + paddingBottom;
		const diffLeft = containerRect.left - blockRect.left + padding;
		const diffRight = blockRect.right - containerRect.right + padding;

		if (diffTop > 0) {
			canvasProps.translateY += diffTop / canvasProps.scale;
		} else if (diffBottom > 0) {
			canvasProps.translateY -= diffBottom / canvasProps.scale;
		}

		if (diffLeft > 0) {
			canvasProps.translateX += diffLeft / canvasProps.scale;
		} else if (diffRight > 0) {
			canvasProps.translateX -= diffRight / canvasProps.scale;
		}
	}

	function setupHistory() {
		canvasHistory.value = useCanvasHistory(rootBlock, selectedBlockIds);
	}

	const resetZoom = () => {
		canvasProps.scale = 1;
		canvasProps.translateX = 0;
		canvasProps.translateY = 0;
	};

	const clearCanvas = () => {
		rootBlock.value = getRootBlockTemplate();
	};

	const moveCanvas = (direction: "up" | "down" | "right" | "left") => {
		if (direction === "up") {
			canvasProps.translateY -= 20;
		} else if (direction === "down") {
			canvasProps.translateY += 20;
		} else if (direction === "right") {
			canvasProps.translateX += 20;
		} else if (direction === "left") {
			canvasProps.translateX -= 20;
		}
	};

	const zoomIn = () => {
		canvasProps.scale = Math.min(canvasProps.scale + 0.1, 10);
	};

	const zoomOut = () => {
		canvasProps.scale = Math.max(canvasProps.scale - 0.1, 0.1);
	};

	function toggleMode(mode: BuilderMode) {
		if (!canvasContainer.value) return;
		const container = canvasContainer.value as HTMLElement;
		if (mode === "text") {
			container.style.cursor = "text";
		} else if (["container", "image", "repeater"].includes(mode)) {
			container.style.cursor = "crosshair";
		} else if (mode === "move") {
			container.style.cursor = "grab";
		} else {
			container.style.cursor = "default";
		}
	}

	function setRootBlock(newBlock: Block, resetCanvas = false) {
		rootBlock.value = newBlock;
		if (canvasHistory.value) {
			canvasHistory.value.dispose();
			setupHistory();
		}
		if (resetCanvas) {
			nextTick(() => {
				setScaleAndTranslate();
				toggleDirty(false);
			});
		}
	}

	const setScaleAndTranslate = async () => {
		if (document.readyState !== "complete") {
			await new Promise((resolve) => {
				window.addEventListener("load", resolve);
			});
		}
		const paddingX = 300;
		const paddingY = 300;

		await nextTick();
		canvasBound.update();
		const containerWidth = containerBound.width;
		const canvasWidth = canvasBound.width / canvasProps.scale;

		canvasProps.scale = containerWidth / (canvasWidth + paddingX * 2);

		canvasProps.translateX = 0;
		canvasProps.translateY = 0;
		await nextTick();
		const scale = canvasProps.scale;
		canvasBound.update();
		const diffY = containerBound.top - canvasBound.top + paddingY * scale;
		if (diffY !== 0) {
			canvasProps.translateY = diffY / scale;
		}
		canvasProps.settingCanvas = false;
	};

	function selectBlock(_block: Block, multiSelect = false) {
		if (multiSelect) {
			selectedBlockIds.value.add(_block.blockId);
		} else {
			selectedBlockIds.value = new Set([_block.blockId]);
		}
	}

	const toggleDirty = (dirty: boolean | null = null) => {
		if (dirty === null) {
			isDirty.value = !isDirty.value;
		} else {
			isDirty.value = dirty;
		}
	};

	function getRootBlock() {
		return rootBlock.value;
	}

	function findBlock(blockId: string, blocks?: Block[]): Block | null {
		if (!blocks) {
			blocks = [getRootBlock()];
		}
		for (const block of blocks) {
			if (block.blockId === blockId) {
				return block;
			}
			if (block.children) {
				const found = findBlock(blockId, block.children);
				if (found) {
					return found;
				}
			}
		}
		return null;
	}

	function removeBlock(block: Block, force: boolean = false) {
		if (block.blockId === "root") {
			toast.warning("Warning", {
				description: "Cannot delete root block",
			});
			return;
		}
		if (block.isChildOfComponentBlock()) {
			block.toggleVisibility(false);
			return;
		}
		const parentBlock = block.parentBlock;
		if (!parentBlock) {
			return;
		}
		const nextSibling = block.getSiblingBlock("next");
		if (canvasStore.activeCanvas?.activeBreakpoint === "desktop" || force) {
			parentBlock.removeChild(block);
		} else {
			block.toggleVisibility(false);
		}
		nextTick(() => {
			if (parentBlock.children.length) {
				if (nextSibling) {
					selectBlock(nextSibling);
				}
			}
		});
	}

	async function scrollBlockIntoView(blockToFocus: Block) {
		return scrollIntoView(
			blockToFocus,
			canvasProps,
			canvasContainer as unknown as Ref<HTMLElement>,
			canvas as unknown as Ref<HTMLElement>,
		);
	}

	return {
		moveCanvas,
		zoomIn,
		zoomOut,
		toggleMode,
		setRootBlock,
		selectBlock,
		toggleDirty,
		findBlock,
		removeBlock,
		scrollBlockIntoView,
		setScaleAndTranslate,
		resetZoom,
		clearCanvas,
		getRootBlock,
		setupHistory,
		isDirty,
	};
}
