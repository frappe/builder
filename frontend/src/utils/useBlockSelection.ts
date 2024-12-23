import Block from "@/utils/block";
import { computed, Ref, ref } from "vue";

export function useBlockSelection(rootBlock: Ref<Block>) {
	const selectedBlockIds = ref<string[]>([]);

	function findBlock(blockId: string, blocks?: Block[]): Block | null {
		if (!blocks) {
			blocks = [rootBlock.value];
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

	const selectedBlocks = computed(() => {
		return selectedBlockIds.value.map((id) => findBlock(id)).filter((b) => b) as Block[];
	});

	const isSelected = (block: Block) => {
		return selectedBlockIds.value.includes(block.blockId);
	};

	const selectBlock = (block: Block, multiSelect = false) => {
		if (multiSelect) {
			selectedBlockIds.value.push(block.blockId);
		} else {
			selectedBlockIds.value = [block.blockId];
		}
	};

	const toggleBlockSelection = (block: Block) => {
		const index = selectedBlockIds.value.indexOf(block.blockId);
		if (index >= 0) {
			selectedBlockIds.value.splice(index, 1);
		} else {
			selectBlock(block, true);
		}
	};

	const clearSelection = () => {
		selectedBlockIds.value = [];
	};

	const selectBlockRange = (newSelectedBlock: Block) => {
		const lastSelectedBlockId = selectedBlockIds.value[selectedBlockIds.value.length - 1];
		const lastSelectedBlock = findBlock(lastSelectedBlockId);
		const lastSelectedBlockParent = lastSelectedBlock?.parentBlock;
		if (!lastSelectedBlock || !lastSelectedBlockParent) {
			newSelectedBlock.selectBlock();
			return;
		}
		const lastSelectedBlockIndex = lastSelectedBlock.parentBlock?.children.indexOf(lastSelectedBlock);
		const newSelectedBlockIndex = newSelectedBlock.parentBlock?.children.indexOf(newSelectedBlock);
		const newSelectedBlockParent = newSelectedBlock.parentBlock;
		if (lastSelectedBlockIndex === undefined || newSelectedBlockIndex === undefined) {
			return;
		}
		const start = Math.min(lastSelectedBlockIndex, newSelectedBlockIndex);
		const end = Math.max(lastSelectedBlockIndex, newSelectedBlockIndex);
		if (lastSelectedBlockParent === newSelectedBlockParent) {
			const blocks = lastSelectedBlockParent.children.slice(start, end + 1);
			selectedBlockIds.value = selectedBlockIds.value.concat(...blocks.map((b) => b.blockId));
			selectedBlockIds.value = Array.from(new Set(selectedBlockIds.value));
		}
	};

	return {
		selectedBlockIds,
		selectedBlocks,
		isSelected,
		selectBlock,
		toggleBlockSelection,
		clearSelection,
		selectBlockRange,
	};
}