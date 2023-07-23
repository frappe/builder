import useStore from "@/store";
import { CSSProperties } from "vue";

const store = useStore();

type styleProperty = keyof CSSProperties;

const blockController = {
	setStyle: (style: any, value: any) => {
		store.builderState.selectedBlocks.forEach((block) => {
			block.setStyle(style, value);
		});
	},
	getStyle: (style: styleProperty) => {
		let styleValue = "__initial__" as StyleValue;
		store.builderState.selectedBlocks.forEach((block) => {
			if (styleValue === "__initial__") {
				styleValue = block.getStyle(style);
			} else if (styleValue !== block.getStyle(style)) {
				styleValue = "Mixed";
			}
		});
		return styleValue;
	},
	isBLockSelected: () => {
		return store.builderState.selectedBlocks.length > 0;
	},
	multipleBlocksSelected: () => {
		return store.builderState.selectedBlocks.length > 1;
	},
	isText: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].isText();
	},
	isContainer: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].isContainer();
	},
	isImage: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].isImage();
	},
	isButton: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].isButton();
	},
	isLink: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].isLink();
	},
	isInput: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].isInput();
	},
	getAttribute: (attribute: string) => {
		let attributeValue = "__initial__" as StyleValue;
		store.builderState.selectedBlocks.forEach((block) => {
			if (attributeValue === "__initial__") {
				attributeValue = block.getAttribute(attribute);
			} else if (attributeValue !== block.getAttribute(attribute)) {
				attributeValue = "Mixed";
			}
		});
		return attributeValue;
	},
	setAttribute: (attribute: string, value: string) => {
		store.builderState.selectedBlocks.forEach((block) => {
			block.setAttribute(attribute, value);
		});
	},
	getKeyValue: (key: "element" | "innerText") => {
		let keyValue = "__initial__" as StyleValue | undefined;
		store.builderState.selectedBlocks.forEach((block) => {
			if (keyValue === "__initial__") {
				keyValue = block[key];
			} else if (keyValue !== block[key]) {
				keyValue = "Mixed";
			}
		});
		return keyValue;
	},
	setKeyValue: (key: "element" | "innerText", value: string) => {
		store.builderState.selectedBlocks.forEach((block) => {
			block[key] = value;
		});
	},
	getRawStyles: () => {
		return blockController.isBLockSelected() && store.builderState.selectedBlocks[0].rawStyles;
	},
	setRawStyles: (rawStyles: BlockStyleMap) => {
		store.builderState.selectedBlocks.forEach((block) => {
			block.rawStyles = rawStyles;
		});
	},
	getParentBlock: () => {
		return store.builderState.selectedBlocks[0].getParentBlock();
	},
	setTextColor: (color: string) => {
		store.builderState.selectedBlocks.forEach((block) => {
			block.setTextColor(color);
		});
	},
	getTextColor: () => {
		let color = "__initial__" as StyleValue;
		store.builderState.selectedBlocks.forEach((block) => {
			if (color === "__initial__") {
				color = block.getTextColor();
			} else if (color !== block.getTextColor()) {
				color = "Mixed";
			}
		});
		return color;
	},
};

export default blockController;
