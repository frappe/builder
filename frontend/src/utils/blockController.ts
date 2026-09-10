import type { default as Block, default as BlockDataKey } from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import getBlockTemplate from "./blockTemplate";
import componentController from "./componentController";
import type { SpacingType } from "./cssUtils";
import { getBlockCopy } from "./helpers";

const canvasStore = useCanvasStore();

const blockController = {
	clearSelection: () => {
		canvasStore.activeCanvas?.clearSelection();
	},
	getFirstSelectedBlock: () => {
		return canvasStore.activeCanvas?.selectedBlocks[0] as Block;
	},
	getSelectedBlocks: () => {
		return canvasStore.activeCanvas?.selectedBlocks || [];
	},
	isRoot() {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isRoot();
	},
	isFlex() {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isFlex();
	},
	isGrid() {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isGrid();
	},
	setStyle: (style: styleProperty, value: StyleValue) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setStyle(style, value);
		});
	},
	setBaseStyle: (style: styleProperty, value: StyleValue) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setBaseStyle(style, value);
		});
	},
	getStyle: (style: styleProperty, nativeOnly?: boolean, cascading?: boolean) => {
		let styleValue = "__initial__" as StyleValue;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (styleValue === "__initial__") {
				styleValue = block.getStyle(style, undefined, nativeOnly, cascading);
			} else if (styleValue !== block.getStyle(style, undefined, nativeOnly, cascading)) {
				styleValue = "Mixed";
			}
		});
		return styleValue;
	},
	getNativeStyle: (style: styleProperty) => {
		let styleValue = "__initial__" as StyleValue;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (styleValue === "__initial__") {
				styleValue = block.getStyle(style, undefined, true);
			} else if (styleValue !== block.getStyle(style, undefined, true)) {
				styleValue = "Mixed";
			}
		});
		return styleValue;
	},
	getCascadingStyle: (style: styleProperty) => {
		let styleValue = "__initial__" as StyleValue;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (styleValue === "__initial__") {
				styleValue = block.getStyle(style, undefined, false, true);
			} else if (styleValue !== block.getStyle(style, undefined, false, true)) {
				styleValue = "Mixed";
			}
		});
		return styleValue;
	},
	isBlockSelected: () => {
		return (canvasStore.activeCanvas?.selectedBlocks.length ?? 0) > 0;
	},
	multipleBlocksSelected: () => {
		return canvasStore.activeCanvas?.selectedBlocks && canvasStore.activeCanvas?.selectedBlocks.length > 1;
	},
	isText: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isText();
	},
	isContainer: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isContainer();
	},
	isImage: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isImage();
	},
	isVideo: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isVideo();
	},
	isButton: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isButton();
	},
	isLink: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isLink();
	},
	isInput: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isInput();
	},
	getAttribute: (attribute: string) => {
		let attributeValue = "__initial__" as StyleValue;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (attributeValue === "__initial__") {
				attributeValue = block.getAttribute(attribute);
			} else if (attributeValue !== block.getAttribute(attribute)) {
				attributeValue = "Mixed";
			}
		});
		return attributeValue;
	},
	setAttribute: (attribute: string, value: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setAttribute(attribute, value);
		});
	},
	removeAttribute: (attribute: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.removeAttribute(attribute);
		});
	},
	getKeyValue: (key: "element" | "innerHTML" | "visibilityCondition") => {
		if (key !== "visibilityCondition") {
			let keyValue = "__initial__" as StyleValue | undefined;
			canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
				let blockKey = block[key] ?? block.referenceComponent?.[key];
				if (keyValue === "__initial__") {
					keyValue = blockKey;
				} else if (keyValue !== blockKey) {
					keyValue = "Mixed";
				}
			});
			return keyValue;
		} else {
			// TODO: handle it better
			let key: string | undefined = "__initial__";
			let comesFrom: "props" | "dataScript" | "componentData" | undefined = undefined;
			canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
				const condition: BlockVisibilityCondition | undefined = block.getVisibilityCondition();
				if (key === "__initial__") {
					if (condition) {
						key = condition.key;
						comesFrom = condition.comesFrom;
					} else {
						key = undefined;
						comesFrom = undefined;
					}
				} else if (condition?.comesFrom !== comesFrom || condition?.key !== key) {
					key = "Mixed";
					comesFrom = undefined;
				}
			});
			return { key, comesFrom };
		}
	},
	setKeyValue: (key: "element" | "innerHTML" | "visibilityCondition", value: any) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (key === "element" && block.blockName === "container") {
				// reset blockName since it will not be a container anymore
				delete block.blockName;
			}
			block[key] = value;
		});
	},
	getClasses: () => {
		let classes = [] as string[];
		if (blockController.isBlockSelected()) {
			classes = blockController.getFirstSelectedBlock().getClasses() || [];
		}
		return classes;
	},
	setClasses: (classes: string[]) => {
		const block = canvasStore.activeCanvas?.selectedBlocks[0];
		if (!block) return;
		block.classes = classes;
	},
	getCustomAttributes: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getCustomAttributes();
	},
	setCustomAttributes: (customAttributes: BlockAttributeMap) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			Object.keys(block.customAttributes).forEach((key) => {
				if (!(key in customAttributes)) {
					delete block.customAttributes[key];
					block.removeDynamicValue(key, "attribute");
				}
			});
			Object.assign(block.customAttributes, customAttributes);
		});
	},
	isClickTrackingEnabled: () => {
		return Boolean(blockController.getCustomAttributes()?.["data-track"]);
	},
	toggleClickTracking: (enabled: boolean) => {
		// Store a marker only; the live blockId is stamped onto data-track at render time.
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (enabled) {
				block.customAttributes["data-track"] = "true";
			} else {
				delete block.customAttributes["data-track"];
				block.removeDynamicValue("data-track", "attribute");
			}
		});
	},
	getParentBlock: () => {
		return canvasStore.activeCanvas?.selectedBlocks[0]?.getParentBlock();
	},
	setTextColor: (color: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setTextColor(color);
		});
	},
	getTextColor: () => {
		let color = "__initial__" as StyleValue;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (color === "__initial__") {
				color = block.getTextColor();
			} else if (color !== block.getTextColor()) {
				color = "Mixed";
			}
		});
		return color;
	},
	setFontFamily: (value: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setFontFamily(value);
		});
	},
	getFontFamily: () => {
		let fontFamily = "__initial__" as StyleValue;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (fontFamily === "__initial__") {
				fontFamily = block.getFontFamily();
			} else if (fontFamily !== block.getFontFamily()) {
				fontFamily = "Mixed";
			}
		});
		return fontFamily;
	},
	isHTML: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isHTML();
	},
	isSVG() {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isSVG();
	},
	getInnerHTML: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getInnerHTML();
	},
	getText: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getText();
	},
	setInnerHTML: (value: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setInnerHTML(value);
		});
	},
	getTextContent: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getTextContent();
	},
	setDataKey: (key: keyof BlockDataKey, value: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			block.setDataKey(key, value);
		});
	},
	getDataKey: (key: keyof BlockDataKey) => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getDataKey(key);
	},
	isRepeater: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().isRepeater();
	},
	getSpacing: (type: SpacingType, opts?: { nativeOnly?: boolean; cascading?: boolean }) => {
		let spacing = "__initial__" as StyleValue;
		blockController.getSelectedBlocks().forEach((block) => {
			const val = block.getSpacing(type, opts);
			if (spacing === "__initial__") {
				spacing = val;
			} else if (spacing !== val) {
				spacing = "Mixed";
			}
		});
		return spacing;
	},
	setSpacing: (type: SpacingType, value: string) => {
		blockController.getSelectedBlocks().forEach((block) => {
			block.setSpacing(type, value);
		});
	},
	toggleAttribute: (attribute: string) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (block.getAttribute(attribute) !== undefined) {
				block.removeAttribute(attribute);
			} else {
				block.setAttribute(attribute, "");
			}
		});
	},
	canHaveChildren: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().canHaveChildren();
	},
	// rendered aspect ratio of the first selected block's canvas element
	getSelectedBlockAspectRatio: (): number | undefined => {
		const block = canvasStore.activeCanvas?.selectedBlocks[0];
		if (!block) return undefined;
		const el = document.querySelector(`[data-block-id="${block.blockId}"]`) as HTMLElement | null;
		return el && el.offsetHeight ? el.offsetWidth / el.offsetHeight : undefined;
	},
	convertToLink: async () => {
		const blocks = blockController.getSelectedBlocks();
		for (const block of blocks) {
			if (block.isSVG() || block.isImage()) {
				const parentBlock = block.getParentBlock();
				if (!parentBlock) continue;
				const newBlockObj = getBlockTemplate("fit-container");
				const newBlock = parentBlock.addChild(newBlockObj, parentBlock.getChildIndex(block));
				newBlock.addChild(block);
				parentBlock.removeChild(block);
				await newBlock.convertToLink();
				newBlock.selectBlock();
			} else {
				await block.convertToLink();
			}
		}
	},
	unsetLink: () => {
		blockController.getSelectedBlocks().forEach((block) => {
			block.unsetLink();
		});
	},
	getBlockProps: () => {
		return blockController.getFirstSelectedBlock()?.getBlockProps();
	},
	setBlockProp: (key: string, value: Record<string, any>) => {
		const allProps = blockController.getBlockProps();
		if (!allProps) return;
		const updatedProps = {
			...allProps,
			[key]: {
				...allProps[key],
				...value,
			},
		};
		blockController.setBlockProps(updatedProps);
	},
	setBlockProps: (props: BlockProps) => {
		const block = blockController.getFirstSelectedBlock();
		if (!block) return;
		block.setBlockProps(props);
		const propsRoot = block.getPropsRoot() || block;
		const allProps = propsRoot.getBlockProps();
		const itemKeys = new Set<string>();
		for (const [propKey, propDetails] of Object.entries(props || {})) {
			if (propDetails?.propOptions?.type === "array") itemKeys.add(propKey);
			if (propKey.endsWith(ITEM_COUNT_SUFFIX)) itemKeys.add(propKey.slice(0, -ITEM_COUNT_SUFFIX.length));
		}
		itemKeys.forEach((itemsKey) => {
			const targetCount = desiredItemCount(allProps, itemsKey);
			if (targetCount !== null) syncArrayPropChildBlocks(propsRoot, itemsKey, targetCount);
		});
	},
};

const ARRAY_ITEMS_ATTRIBUTE = "data-array-items";

function collectArrayItemContainers(block: Block, propKey: string, found: Block[] = []): Block[] {
	if (block.getAttributes()[ARRAY_ITEMS_ATTRIBUTE] === propKey) {
		found.push(block);
	}
	(block.children || []).forEach((child) => collectArrayItemContainers(child, propKey, found));
	return found;
}

function firstChildBearingContainer(block: Block): Block | null {
	if (block.children && block.children.length > 0) {
		return block.children.find((c) => c.children && c.children.length > 0) || block;
	}
	return block.canHaveChildren() ? block : null;
}

function syncContainerToCount(container: Block, targetCount: number) {
	if (!container.children || container.children.length === 0) return;

	const templateChild = container.children[0];
	const baseName = (templateChild.blockName || "Item").replace(/\s*\d+$/, "");

	while (container.children.length < targetCount) {
		const newChild = getBlockCopy(templateChild);
		newChild.blockName = `${baseName} ${container.children.length + 1}`;
		container.addChild(newChild, null, false);
	}

	while (container.children.length > targetCount && container.children.length > 1) {
		container.removeChild(container.children[container.children.length - 1]);
	}
}

const ITEM_COUNT_SUFFIX = "_count";

function parseArrayValue(rawValue: any): any[] | null {
	if (Array.isArray(rawValue)) return rawValue;
	if (typeof rawValue === "string") {
		try {
			const parsed = JSON.parse(rawValue);
			return Array.isArray(parsed) ? parsed : null;
		} catch {
			return null;
		}
	}
	return null;
}

function desiredItemCount(allProps: BlockProps, itemsKey: string): number | null {
	const arrayProp = allProps[itemsKey];
	const countProp = allProps[`${itemsKey}${ITEM_COUNT_SUFFIX}`];

	if (!arrayProp && !countProp) return null;
	if (arrayProp && arrayProp.propOptions?.type !== "array") return null;

	let fromArray = 0;
	if (arrayProp) {
		const entries = parseArrayValue(arrayProp.value);
		if (entries === null && arrayProp.value != null) return null;
		fromArray = entries?.length ?? 0;
	}

	const rawCount = countProp ? countProp.value ?? countProp.propOptions?.options?.defaultValue : 0;
	const fromCount = Math.floor(Number(rawCount) || 0);

	return Math.max(fromArray, Math.max(fromCount, 0));
}

function syncArrayPropChildBlocks(block: Block, itemsKey: string, targetCount: number) {
	const marked = collectArrayItemContainers(block, itemsKey);
	const containers = marked.length ? marked : [firstChildBearingContainer(block)];
	containers.forEach((container) => container && syncContainerToCount(container, targetCount));
}

export default blockController;
