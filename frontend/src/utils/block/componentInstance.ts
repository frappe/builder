import type Block from "@/block";
import { resetBlock } from "@/utils/block/tree";
import { deepEqual, diffArray, getBlockCopy } from "@/utils/helpers";
import { toRaw } from "vue";

export function extendWithComponent(
	block: Block | BlockOptions,
	extendedFromComponent: string | undefined,
	componentChildren: Block[],
	resetOverrides: boolean = true,
) {
	resetBlock(block, false, resetOverrides);
	block.children?.forEach((child, index) => {
		child.isChildOfComponent = extendedFromComponent;
		const componentChild = componentChildren[index];
		if (child.extendedFromComponent) {
			const component = child.referenceComponent;
			child.referenceBlockId = componentChild.blockId;
			extendWithComponent(child, child.extendedFromComponent, component.children, false);
		} else if (componentChild) {
			child.referenceBlockId = componentChild.blockId;
			extendWithComponent(child, extendedFromComponent, componentChild.children, resetOverrides);
		}
	});
}

export function resetWithComponent(
	block: Block | BlockOptions,
	extendedWithComponent: string,
	componentChildren: Block[],
	resetOverrides: boolean = true,
) {
	block = toRaw(block);
	resetBlock(block, true, resetOverrides);
	block.children?.splice(0, block.children.length);
	componentChildren.forEach((componentChild) => {
		const blockComponent = getBlockCopy(componentChild);
		blockComponent.isChildOfComponent = extendedWithComponent;
		blockComponent.referenceBlockId = componentChild.blockId;
		if (!blockComponent.extendedFromComponent) {
			blockComponent.componentVersion = block.componentVersion;
		}
		const childBlock = block.addChild(blockComponent, null, false);
		if (componentChild.extendedFromComponent) {
			const component = childBlock.referenceComponent;
			resetWithComponent(childBlock, componentChild.extendedFromComponent, component.children, false);
		} else {
			resetWithComponent(childBlock, extendedWithComponent, componentChild.children, resetOverrides);
		}
	});
}

export function syncBlockWithComponent(
	parentBlock: Block,
	block: Block,
	componentName: string,
	componentChildren: Block[],
) {
	componentChildren.forEach((componentChild, index) => {
		const blockExists = findComponentBlock(componentChild.blockId, parentBlock.children);
		if (!blockExists) {
			const blockComponent = getBlockCopy(componentChild);
			blockComponent.isChildOfComponent = componentName;
			blockComponent.referenceBlockId = componentChild.blockId;
			resetBlock(blockComponent);
			resetWithComponent(blockComponent, componentName, componentChild.children);
			block.addChild(blockComponent, index, false);
		}
	});

	block.children.forEach((child) => {
		const componentChild = componentChildren.find((c) => c.blockId === child.referenceBlockId);
		if (componentChild) {
			syncBlockWithComponent(parentBlock, child, componentName, componentChild.children);
		}
	});
}

export function rebuildWithComponent(
	block: Block,
	componentId: string,
	componentChildren: Block[],
	oldComponentChildren: Block[],
) {
	rebuildComponentChildren(
		block,
		componentId,
		componentChildren,
		indexChildrenByRefId(block.children),
		indexChildrenByBlockId(oldComponentChildren),
	);
}

function rebuildComponentChildren(
	block: Block,
	componentId: string,
	componentChildren: Block[],
	oldChildrenByRefId: Map<string, Block>,
	oldComponentChildrenByBlockId: Map<string, Block>,
) {
	// Component subtrees mirror the new version exactly; only overrides matched by reference ID survive.
	block = toRaw(block);
	block.children.splice(0, block.children.length);
	componentChildren.forEach((componentChild) => {
		const fresh = getBlockCopy(componentChild);
		fresh.isChildOfComponent = componentId;
		fresh.referenceBlockId = componentChild.blockId;
		if (!fresh.extendedFromComponent) {
			fresh.componentVersion = block.componentVersion;
		}
		const matched = oldChildrenByRefId.get(componentChild.blockId);
		const oldComponentChild = oldComponentChildrenByBlockId.get(componentChild.blockId);
		if (matched && oldComponentChild && !fresh.extendedFromComponent) {
			copyUserOverrides(matched, fresh, oldComponentChild);
		}
		const childBlock = block.addChild(fresh, null, false);
		if (componentChild.extendedFromComponent) {
			const nestedComponent = childBlock.referenceComponent;
			if (nestedComponent) {
				resetWithComponent(childBlock, componentChild.extendedFromComponent, nestedComponent.children, false);
			}
		} else {
			rebuildComponentChildren(
				childBlock,
				componentId,
				componentChild.children,
				indexChildrenByRefId(matched?.children),
				indexChildrenByBlockId(oldComponentChild?.children),
			);
		}
	});
}

function copyUserOverrides(src: Block, dst: Block, oldComponentChild: Block) {
	mergeOverrideMap(src.baseStyles, oldComponentChild.baseStyles, dst.baseStyles);
	mergeOverrideMap(src.rawStyles, oldComponentChild.rawStyles, dst.rawStyles);
	mergeOverrideMap(src.mobileStyles, oldComponentChild.mobileStyles, dst.mobileStyles);
	mergeOverrideMap(src.tabletStyles, oldComponentChild.tabletStyles, dst.tabletStyles);
	mergeOverrideMap(src.attributes, oldComponentChild.attributes, dst.attributes);
	mergeOverrideMap(src.customAttributes, oldComponentChild.customAttributes, dst.customAttributes);
	dst.props = mergeOverrideProps(src.props, oldComponentChild.props, dst.props || {});
	if (src.classes) {
		dst.classes = [...(dst.classes || []), ...diffArray(src.classes, oldComponentChild.classes)];
	}
	if (src.dynamicValues) {
		dst.dynamicValues = [
			...(dst.dynamicValues || []),
			...diffArray(src.dynamicValues, oldComponentChild.dynamicValues),
		];
	}
	if (src.innerHTML !== undefined && !deepEqual(src.innerHTML, oldComponentChild.innerHTML)) {
		dst.innerHTML = src.innerHTML;
	}
	if (src.dataKey && !deepEqual(src.dataKey, oldComponentChild.dataKey)) {
		dst.dataKey = src.dataKey;
	}
	if (src.visibilityCondition && !deepEqual(src.visibilityCondition, oldComponentChild.visibilityCondition)) {
		dst.visibilityCondition = src.visibilityCondition;
	}
}

function mergeOverrideMap(
	src: Record<string, any> | undefined,
	oldComp: Record<string, any> | undefined,
	dst: Record<string, any>,
) {
	for (const key of Object.keys(src || {})) {
		if (!deepEqual(src?.[key], oldComp?.[key])) {
			dst[key] = src?.[key];
		}
	}
}

function mergeOverrideProps(
	src: Record<string, any> | undefined,
	oldComp: Record<string, any> | undefined,
	dstProps: Record<string, any>,
): Record<string, any> {
	// The new component's prop schema decides which override keys remain valid.
	const result: Record<string, any> = {};
	for (const key of Object.keys(dstProps)) {
		if (src && key in src && !deepEqual(src[key], oldComp?.[key])) {
			result[key] = src[key];
		} else {
			result[key] = dstProps[key];
		}
	}
	return result;
}

function indexChildrenByRefId(children: Block[] | undefined): Map<string, Block> {
	const map = new Map<string, Block>();
	(children || []).forEach((child) => {
		if (child.referenceBlockId) {
			map.set(child.referenceBlockId, child);
		}
	});
	return map;
}

function indexChildrenByBlockId(children: Block[] | undefined): Map<string, Block> {
	const map = new Map<string, Block>();
	(children || []).forEach((child) => {
		if (child.blockId) {
			map.set(child.blockId, child);
		}
	});
	return map;
}

function findComponentBlock(blockId: string, blocks: Block[]): Block | null {
	for (const block of blocks) {
		if (block.referenceBlockId === blockId) {
			return block;
		}
		if (block.children) {
			const found = findComponentBlock(blockId, block.children);
			if (found) {
				return found;
			}
		}
	}
	return null;
}
