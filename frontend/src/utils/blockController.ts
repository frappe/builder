import useStore from "@/store";

const store = useStore();

import { CSSProperties } from "vue";

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
	}
};

export default blockController;
