import type Block from "@/block";
import type { RegistryEntry } from "@/utils/createRegistry";

// the menu opens from the canvas and from the layers panel, so an item needs the
// event target and the origin as well as the block
export type BlockMenuContext = {
	block: Block;
	target: HTMLElement;
	fromLayersPanel: boolean;
};

export type ContextMenuOption = RegistryEntry & {
	label: string;
	action: (context: BlockMenuContext) => void;
	condition?: (context: BlockMenuContext) => boolean;
	disabled?: (context: BlockMenuContext) => boolean;
};
