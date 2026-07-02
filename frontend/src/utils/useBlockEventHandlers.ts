import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import getBlockTemplate from "@/utils/blockTemplate";
import { getBlock, getBlockInfo, isBlock } from "@/utils/helpers";
import { getEventPointInEditor } from "@/utils/canvasFrameDom";
import { nextTick } from "vue";

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

export function useBlockEventHandlers(target: HTMLElement) {
	target.addEventListener("click", handleBlockClick);
	target.addEventListener("dblclick", handleBlockDoubleClick);
	target.addEventListener("contextmenu", handleBlockContextMenu);

	return () => {
		target.removeEventListener("click", handleBlockClick);
		target.removeEventListener("dblclick", handleBlockDoubleClick);
		target.removeEventListener("contextmenu", handleBlockContextMenu);
	};
}

export function handleBlockClick(e: MouseEvent) {
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

export function handleBlockDoubleClick(e: MouseEvent) {
	if (!isBlock(e) || isEditable(e)) return;
	canvasStore.editableBlock = null;
	const block = getBlock(e);
	if (!block) return;
	if (block.isImage()) {
		nextTick(() => {
			builderStore.openImageUpload = true;
		});
		e.stopPropagation();
		return;
	}
	if (block.isText() || block.isLink() || block.isButton()) {
		canvasStore.editableBlock = block;
		e.stopPropagation();
	}

	// dblclick on container adds text block or selects text block if only one child
	let children = block.getChildren();
	if (block.isHTML()) {
		document
			.querySelector(`.editor[data-block-id="${block.blockId}"]`)
			?.dispatchEvent(new MouseEvent("dblclick", { bubbles: true, cancelable: true }));
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

export function handleBlockContextMenu(e: MouseEvent) {
	if (!isBlock(e) || isEditable(e)) return;
	const block = getBlock(e);
	const { blockId } = getBlockInfo(e);
	if (block && block.isRoot()) return;
	e.stopPropagation();
	e.preventDefault();
	selectBlock(e);
	const point = getEventPointInEditor(e);
	nextTick(() => {
		document.querySelector(`.editor[data-block-id="${blockId}"]`)?.dispatchEvent(
			new MouseEvent("contextmenu", {
				bubbles: true,
				cancelable: true,
				clientX: point.x,
				clientY: point.y,
			}),
		);
	});
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

	if (builderStore.leftPanelActiveTab !== "Code") builderStore.leftPanelActiveTab = "Layers";
};
