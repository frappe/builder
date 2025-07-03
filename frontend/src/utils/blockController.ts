import type Block from "@/block";
import type { BlockDataKey } from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { nextTick } from "vue";
import getBlockTemplate from "./blockTemplate";

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
		return canvasStore.activeCanvas?.selectedBlocks.length || 0 > 0;
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
		let keyValue = "__initial__" as StyleValue | undefined;
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			if (keyValue === "__initial__") {
				keyValue = block[key];
			} else if (keyValue !== block[key]) {
				keyValue = "Mixed";
			}
		});
		return keyValue;
	},
	setKeyValue: (key: "element" | "innerHTML" | "visibilityCondition", value: string) => {
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
	getRawStyles: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getRawStyles();
	},
	setRawStyles: (rawStyles: BlockStyleMap) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			Object.keys(block.rawStyles).forEach((key) => {
				if (!rawStyles[key]) {
					delete block.rawStyles[key];
				}
			});
			Object.assign(block.rawStyles, rawStyles);
		});
	},
	getCustomAttributes: () => {
		return blockController.isBlockSelected() && blockController.getFirstSelectedBlock().getCustomAttributes();
	},
	setCustomAttributes: (customAttributes: BlockAttributeMap) => {
		canvasStore.activeCanvas?.selectedBlocks.forEach((block) => {
			Object.keys(block.customAttributes).forEach((key) => {
				if (!customAttributes[key]) {
					delete block.customAttributes[key];
				}
			});
			Object.assign(block.customAttributes, customAttributes);
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
	getPadding: (opts?: { nativeOnly?: boolean; cascading?: boolean }) => {
		let padding = "__initial__" as StyleValue;
		blockController.getSelectedBlocks().forEach((block) => {
			const val = block.getPadding(opts);
			if (padding === "__initial__") {
				padding = val;
			} else if (padding !== val) {
				padding = "Mixed";
			}
		});
		return padding;
	},
	setPadding: (value: string) => {
		blockController.getSelectedBlocks().forEach((block) => {
			block.setPadding(value);
		});
	},
	getMargin: (opts?: { nativeOnly?: boolean; cascading?: boolean }) => {
		let margin = "__initial__" as StyleValue;
		blockController.getSelectedBlocks().forEach((block) => {
			const val = block.getMargin(opts);
			if (margin === "__initial__") {
				margin = val;
			} else if (margin !== val) {
				margin = "Mixed";
			}
		});
		return margin;
	},
	setMargin: (value: string) => {
		blockController.getSelectedBlocks().forEach((block) => {
			block.setMargin(value);
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
	convertToLink: () => {
		blockController.getSelectedBlocks().forEach((block: Block) => {
			if (block.isSVG() || block.isImage()) {
				const parentBlock = block.getParentBlock();
				if (!parentBlock) return;
				const newBlockObj = getBlockTemplate("fit-container");
				const newBlock = parentBlock.addChild(newBlockObj, parentBlock.getChildIndex(block));
				newBlock.addChild(block);
				parentBlock.removeChild(block);
				newBlock.convertToLink();
				nextTick(() => {
					newBlock.selectBlock();
				});
			} else {
				block.convertToLink();
			}
		});
	},
	unsetLink: () => {
		blockController.getSelectedBlocks().forEach((block) => {
			block.unsetLink();
		});
	},
};

export default blockController;
