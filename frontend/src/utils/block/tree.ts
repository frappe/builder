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
		block.rawStyles = {};
		block.mobileStyles = {};
		block.tabletStyles = {};
		block.attributes = {};
		block.customAttributes = {};
		block.classes = [];
		block.dataKey = null;
		block.dynamicValues = [];
		block.props = {};
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
