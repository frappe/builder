import type Block from "@/block";
import { computed, Ref, ref } from "vue";

export function useBlockSelection(rootBlock: Ref<Block>) {
	const selectedBlockIds = ref<Set<string>>(new Set());

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
		return Array.from(selectedBlockIds.value)
			.map((id: string) => findBlock(id))
			.filter((b): b is Block => !!b);
	});

	const isSelected = (block: Block) => {
		return selectedBlockIds.value.has(block.blockId);
	};

	const selectBlock = (block: Block, multiSelect = false) => {
		if (multiSelect) {
			selectedBlockIds.value.add(block.blockId);
		} else {
			selectedBlockIds.value = new Set([block.blockId]);
		}
	};

	const toggleBlockSelection = (block: Block) => {
		if (selectedBlockIds.value.has(block.blockId)) {
			selectedBlockIds.value.delete(block.blockId);
		} else {
			selectBlock(block, true);
		}
	};

	const clearSelection = () => {
		selectedBlockIds.value = new Set();
	};

	const selectBlockRange = (newSelectedBlock: Block) => {
		const lastSelectedBlockId = Array.from(selectedBlockIds.value)[selectedBlockIds.value.size - 1];
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
			blocks.forEach((b) => selectedBlockIds.value.add(b.blockId));
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
