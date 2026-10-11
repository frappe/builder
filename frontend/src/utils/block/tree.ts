import type Block from "@/block";
import { generateId } from "@/utils/helpers";

export function resetBlock(
	block: Block | BlockOptions,
	resetChildren: boolean = true,
	resetOverrides: boolean = true,
) {
	block.blockId = generateId();
	if (resetOverrides) {
		delete block.innerHTML;
		delete block.element;
		block.baseStyles = {};
		block.mobileStyles = {};
		block.tabletStyles = {};
		block.attributes = {};
		block.customAttributes = {};
		block.classes = [];
		block.dataKey = null;
		block.dynamicValues = [];
		block.props = {};
		block.clientScript = {};
		// @ts-ignore
		delete block.blockClientScript;
	}

	if (resetChildren) {
		block.children?.forEach((child) => {
			resetBlock(child, resetChildren, !Boolean(child.extendedFromComponent));
		});
	}
}

export function findBlockInTree(blockId: string, blocks: Block[]): Block | null {
	for (const block of blocks) {
		if (block.blockId === blockId) {
			return block;
		}
		if (block.children) {
			const found = findBlockInTree(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
}

// each scope block and its descendants once, in tree order; ids missing from the tree (deleted blocks) are skipped
export function getBlocksInScope(rootBlock: Block, scopeBlockIds: string[]): Block[] {
	const scope = new Set(scopeBlockIds);
	const blocks: Block[] = [];
	function addBlock(block: Block, ancestorInScope: boolean) {
		const inScope = ancestorInScope || !scope.size || scope.has(block.blockId);
		if (inScope) blocks.push(block);
		block.children?.forEach((child) => addBlock(child, inScope));
	}
	addBlock(rootBlock, false);
	return blocks;
}
