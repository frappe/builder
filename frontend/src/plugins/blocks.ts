import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import { getBlockInstance } from "@/utils/helpers";

/** The drag data type the canvas reads a plugin's block from. */
export const PLUGIN_BLOCK_TYPE = "builder/plugin-block";

/**
 * Puts a plugin's block where the user is working: inside the selected container,
 * after any other selected block, or at the end of the page. It is selected and
 * returned, and one Cmd+Z takes it out again.
 */
export function insertBlock(options: BlockOptions): Block | undefined {
	const block = freshBlock(options);
	const target = outsideComponent(blockController.getFirstSelectedBlock());
	if (!target) return useCanvasStore().activeCanvas?.getRootBlock().addChild(block);
	return addBeside(target, block);
}

/** Call from a draggable element's dragstart; the canvas inserts the block where it is dropped. */
export function startBlockDrag(event: DragEvent, options: BlockOptions) {
	event.dataTransfer?.setData(PLUGIN_BLOCK_TYPE, JSON.stringify(options));
	useCanvasStore().handleDragStart(event);
}

/** Into a block that takes children, else right after it. */
export function addBeside(target: Block, block: BlockOptions | Block, index?: number | null) {
	if (target.canHaveChildren()) return target.addChild(block, index);
	return target.getParentBlock()?.addChildAfter(block, target);
}

/** New ids every time, so inserting the same item twice gives two blocks. */
export function freshBlock(options: BlockOptions | string): Block {
	return getBlockInstance(typeof options === "string" ? options : JSON.stringify(options), false);
}

// a component instance's inner blocks mirror the component, so new blocks go beside the instance
function outsideComponent(block: Block | null): Block | null {
	while (block?.isChildOfComponent) block = block.getParentBlock();
	return block;
}
