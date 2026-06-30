import InlineInput from "@/components/Controls/InlineInput.vue";
import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import blockController from "@/utils/blockController";
import { toast } from "frappe-ui";

const walkBlocks = (block: Block, visit: (block: Block) => void, isRoot = false) => {
	if (!isRoot && block.extendedFromComponent) return;
	visit(block);
	block.children.forEach((child) => walkBlocks(child, visit));
};

const canDeclareSlot = () => {
	const block = blockController.getFirstSelectedBlock();
	if (!block?.isContainer() || block.isRepeater() || block.isExtendedFromComponent()) return false;

	let parent = block.getParentBlock();
	while (parent) {
		if (parent.isSlot() || parent.isRepeater()) return false;
		parent = parent.getParentBlock();
	}

	let hasNestedSlot = false;
	block.children.forEach((child) =>
		walkBlocks(child, (descendant) => {
			if (descendant.isSlot()) hasNestedSlot = true;
		}),
	);
	return !hasNestedSlot;
};

const setSlotName = (value: string) => {
	const block = blockController.getFirstSelectedBlock();
	const root = useCanvasStore().activeCanvas?.getRootBlock();
	if (!block || !root) return;

	const slotName = value.trim();
	if (!slotName) {
		delete block.slotName;
		delete block.slotFilled;
		return;
	}

	let duplicate = false;
	walkBlocks(
		root,
		(candidate) => {
			if (candidate !== block && candidate.slotName === slotName) duplicate = true;
		},
		true,
	);
	if (duplicate) {
		toast.error(`A slot named "${slotName}" already exists`);
		return;
	}
	block.slotName = slotName;
};

export default {
	name: "Component Slot",
	properties: [
		{
			component: InlineInput,
			getProps: () => ({
				label: "Slot Name",
				modelValue: blockController.getFirstSelectedBlock()?.slotName || "",
				placeholder: "e.g. content",
				description: "Page blocks can be placed here without changing the component structure.",
			}),
			events: {
				"update:modelValue": setSlotName,
			},
			searchKeyWords: "Component, Slot, Slot Name, Content",
		},
	],
	condition: () =>
		!blockController.multipleBlocksSelected() &&
		useCanvasStore().editingMode === "fragment" &&
		canDeclareSlot(),
};
