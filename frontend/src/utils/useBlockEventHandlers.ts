import useStore from "@/store";
import getBlockTemplate from "@/utils/blockTemplate";
import { useEventListener } from "@vueuse/core";
import { nextTick } from "vue";

const store = useStore();

export function useBlockEventHandlers() {
	useEventListener(document, "click", handleClick);
	useEventListener(document, "dblclick", handleDoubleClick);
	useEventListener(document, "mouseover", handleMouseOver);
	useEventListener(document, "mouseleave", handleMouseLeave);
	useEventListener(document, "contextmenu", triggerContextMenu);

	function handleClick(e: MouseEvent) {
		if (!isBlock(e) || isEditable(e)) return;
		if (store.preventClick) {
			e.stopPropagation();
			e.preventDefault();
			store.preventClick = false;
			return;
		}
		selectBlock(e);
		e.stopPropagation();
		e.preventDefault();
	}

	function handleDoubleClick(e: MouseEvent) {
		if (!isBlock(e) || isEditable(e)) return;
		store.editableBlock = null;
		const block = getBlock(e);
		if (!block) return;
		if (block.isText() || block.isLink() || block.isButton()) {
			store.editableBlock = block;
			e.stopPropagation();
		}

		// dblclick on container adds text block or selects text block if only one child
		let children = block.getChildren();
		if (block.isHTML()) {
			// editor.value?.element.dispatchEvent(new MouseEvent("dblclick", e));
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

	function handleMouseOver(e: MouseEvent) {
		if (!isBlock(e)) return;
		if (store.mode === "move") return;
		const block = getBlock(e);
		const { breakpoint } = getBlockInfo(e);
		store.hoveredBlock = block?.blockId || null;
		store.hoveredBreakpoint = breakpoint;
		e.stopPropagation();
	}

	function handleMouseLeave(e: MouseEvent) {
		if (!isBlock(e)) return;
		if (store.mode === "move") return;
		const block = getBlock(e);
		if (store.hoveredBlock === block?.blockId) {
			store.hoveredBlock = null;
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
				.querySelector(`.editor[data-block-id=${blockId}]`)
				?.dispatchEvent(new MouseEvent("contextmenu", e));
		});
	}
}

function getBlock(e: MouseEvent) {
	const blockInfo = getBlockInfo(e);
	return store.activeCanvas?.findBlock(blockInfo.blockId);
}

const isEditable = (e: MouseEvent) => {
	const { blockId, breakpoint } = getBlockInfo(e);
	// to ensure it is right block and not on different breakpoint
	return store.editableBlock?.blockId === blockId && store.activeBreakpoint === breakpoint;
};

function isBlock(e: MouseEvent) {
	return e.target instanceof HTMLElement && e.target.closest(".__builder_component__");
}

const selectBlock = (e: MouseEvent) => {
	if (isEditable(e) || store.mode !== "select") {
		return;
	}
	const block = getBlock(e);
	const { breakpoint } = getBlockInfo(e);
	if (!block) return;
	store.selectBlock(block, e);
	store.activeBreakpoint = breakpoint;

	store.leftPanelActiveTab = "Layers";
	store.rightPanelActiveTab = "Properties";
};

type BlockInfo = {
	blockId: string;
	breakpoint: string;
};

const getBlockInfo = (e: MouseEvent) => {
	const target = (e.target as HTMLElement)?.closest(".__builder_component__") as HTMLElement;
	return target.dataset as BlockInfo;
};
