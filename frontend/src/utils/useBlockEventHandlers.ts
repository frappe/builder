import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import getBlockTemplate from "@/utils/blockTemplate";
import { getBlock, getBlockInfo, isBlock } from "@/utils/helpers";
import { useEventListener } from "@vueuse/core";
import { nextTick } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

export function useBlockEventHandlers(target: HTMLElement) {
	useEventListener(target, "click", handleClick);
	useEventListener(target, "dblclick", handleDoubleClick);
	useEventListener(target, "contextmenu", triggerContextMenu);

	function handleClick(e: MouseEvent) {
		if (!isBlock(e) || isEditable(e)) return;
		if (canvasStore.preventClick) {
			e.stopPropagation();
			e.preventDefault();
			canvasStore.preventClick = false;
			return;
		}
		selectBlock(e);
		e.stopPropagation();
		e.preventDefault();
	}

	function handleDoubleClick(e: MouseEvent) {
		if (!isBlock(e) || isEditable(e)) return;
		canvasStore.editableBlock = null;
		const block = getBlock(e);
		if (!block) return;
		if (block.isText() || block.isLink() || block.isButton()) {
			canvasStore.editableBlock = block;
			e.stopPropagation();
		}

		// dblclick on container adds text block or selects text block if only one child
		let children = block.getChildren();
		if (block.isHTML()) {
			document
				.querySelector(`.editor[data-block-id="${block.blockId}"]`)
				?.dispatchEvent(new MouseEvent("dblclick", e));
			e.stopPropagation();
		} else if (block.isContainer()) {
			if (!children.length) {
				const child = getBlockTemplate("text");
				block.setBaseStyle("alignItems", "center");
				block.setBaseStyle("justifyContent", "center");
				const childBlock = block.addChild(child);
				childBlock.makeBlockEditable();
			} else if (children.length === 1 && children[0].isText()) {
				const child = children[0];
				child.makeBlockEditable();
			}
			e.stopPropagation();
		}
	}

	function triggerContextMenu(e: MouseEvent) {
		if (!isBlock(e) || isEditable(e)) return;
		const block = getBlock(e);
		const { blockId } = getBlockInfo(e);
		if (block && block.isRoot()) return;
		e.stopPropagation();
		e.preventDefault();
		selectBlock(e);
		nextTick(() => {
			document
				.querySelector(`.editor[data-block-id="${blockId}"]`)
				?.dispatchEvent(new MouseEvent("contextmenu", e));
		});
	}
}

const isEditable = (e: MouseEvent) => {
	const { blockId, breakpoint } = getBlockInfo(e);
	// to ensure it is right block and not on different breakpoint
	return (
		canvasStore.editableBlock?.blockId === blockId &&
		canvasStore.activeCanvas?.activeBreakpoint === breakpoint
	);
};

const selectBlock = (e: MouseEvent) => {
	if (isEditable(e) || builderStore.mode !== "select") {
		return;
	}
	const block = getBlock(e);
	const { breakpoint } = getBlockInfo(e);
	if (!block) return;
	canvasStore.selectBlock(block, e);
	canvasStore.activeCanvas?.setActiveBreakpoint(breakpoint);

	builderStore.leftPanelActiveTab = "Layers";
	builderStore.rightPanelActiveTab = "Properties";
};
