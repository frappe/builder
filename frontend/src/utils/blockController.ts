import useStore from "@/store";
import { CSSProperties } from "vue";
import { BlockDataKey } from "./block";

const store = useStore();

type styleProperty = keyof CSSProperties;

const blockController = {
	clearSelection: () => {
		store.selectedBlocks = [];
	},
	getSelectedBlocks: () => {
		return store.selectedBlocks;
	},
	isRoot() {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isRoot();
	},
	setStyle: (style: styleProperty, value: StyleValue) => {
		store.selectedBlocks.forEach((block) => {
			block.setStyle(style, value);
		});
	},
	setBaseStyle: (style: styleProperty, value: StyleValue) => {
		store.selectedBlocks.forEach((block) => {
			block.setBaseStyle(style, value);
		});
	},
	getStyle: (style: styleProperty) => {
		let styleValue = "__initial__" as StyleValue;
		store.selectedBlocks.forEach((block) => {
			if (styleValue === "__initial__") {
				styleValue = block.getStyle(style);
			} else if (styleValue !== block.getStyle(style)) {
				styleValue = "Mixed";
			}
		});
		return styleValue;
	},
	isBLockSelected: () => {
		return store.selectedBlocks.length > 0;
	},
	multipleBlocksSelected: () => {
		return store.selectedBlocks.length > 1;
	},
	isText: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isText();
	},
	isContainer: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isContainer();
	},
	isImage: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isImage();
	},
	isButton: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isButton();
	},
	isLink: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isLink();
	},
	isInput: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isInput();
	},
	getAttribute: (attribute: string) => {
		let attributeValue = "__initial__" as StyleValue;
		store.selectedBlocks.forEach((block) => {
			if (attributeValue === "__initial__") {
				attributeValue = block.getAttribute(attribute);
			} else if (attributeValue !== block.getAttribute(attribute)) {
				attributeValue = "Mixed";
			}
		});
		return attributeValue;
	},
	setAttribute: (attribute: string, value: string) => {
		store.selectedBlocks.forEach((block) => {
			block.setAttribute(attribute, value);
		});
	},
	getKeyValue: (key: "element" | "innerHTML" | "visibilityCondition") => {
		let keyValue = "__initial__" as StyleValue | undefined;
		store.selectedBlocks.forEach((block) => {
			if (keyValue === "__initial__") {
				keyValue = block[key];
			} else if (keyValue !== block[key]) {
				keyValue = "Mixed";
			}
		});
		return keyValue;
	},
	setKeyValue: (key: "element" | "innerHTML" | "visibilityCondition", value: string) => {
		store.selectedBlocks.forEach((block) => {
			if (key === "element" && block.blockName === "container") {
				// reset blockName since it will not be a container anymore
				delete block.blockName;
			}
			block[key] = value;
		});
	},
	getClasses: () => {
		let classes = [] as string[];
		classes = store.selectedBlocks[0].getClasses();
		return classes;
	},
	setClasses: (classes: string[]) => {
		store.selectedBlocks[0].classes = classes;
	},
	getRawStyles: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].rawStyles;
	},
	setRawStyles: (rawStyles: BlockStyleMap) => {
		store.selectedBlocks.forEach((block) => {
			block.rawStyles = rawStyles;
		});
	},
	getCustomAttributes: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].customAttributes;
	},
	setCustomAttributes: (customAttributes: BlockAttributeMap) => {
		store.selectedBlocks.forEach((block) => {
			block.customAttributes = customAttributes;
		});
	},
	getParentBlock: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].getParentBlock();
	},
	setTextColor: (color: string) => {
		store.selectedBlocks.forEach((block) => {
			block.setTextColor(color);
		});
	},
	getTextColor: () => {
		let color = "__initial__" as StyleValue;
		store.selectedBlocks.forEach((block) => {
			if (color === "__initial__") {
				color = block.getTextColor();
			} else if (color !== block.getTextColor()) {
				color = "Mixed";
			}
		});
		return color;
	},
	setFontFamily: (value: string) => {
		store.selectedBlocks.forEach((block) => {
			block.setFontFamily(value);
		});
	},
	getFontFamily: () => {
		let fontFamily = "__initial__" as StyleValue;
		store.selectedBlocks.forEach((block) => {
			if (fontFamily === "__initial__") {
				fontFamily = block.getFontFamily();
			} else if (fontFamily !== block.getFontFamily()) {
				fontFamily = "Mixed";
			}
		});
		return fontFamily;
	},
	isHTML: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isHTML();
	},
	getInnerHTML: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].getInnerHTML();
	},
	setInnerHTML: (value: string) => {
		store.selectedBlocks.forEach((block) => {
			block.setInnerHTML(value);
		});
	},
	getTextContent: () => {
		return store.selectedBlocks[0].getTextContent();
	},
	setDataKey: (key: keyof BlockDataKey, value: string) => {
		store.selectedBlocks.forEach((block) => {
			block.setDataKey(key, value);
		});
	},
	getDataKey: (key: keyof BlockDataKey) => {
		return store.selectedBlocks[0].getDataKey(key);
	},
	isRepeater: () => {
		return blockController.isBLockSelected() && store.selectedBlocks[0].isRepeater();
	},
	getPadding: () => {
		return store.selectedBlocks[0].getPadding();
	},
	setPadding: (value: string) => {
		store.selectedBlocks[0].setPadding(value);
	},
	getMargin: () => {
		return store.selectedBlocks[0].getMargin();
	},
	setMargin: (value: string) => {
		store.selectedBlocks[0].setMargin(value);
	},
};

export default blockController;
