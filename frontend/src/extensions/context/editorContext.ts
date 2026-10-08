/**
 * The live state of Builder that an extension can read. It is one computed for all readers.
 * The getter gets the stores. So the load order of the editor does not matter.
 */

import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import type { BlockSnapshot, Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/** Makes a snapshot of one block. */
export const getBlockSnapshot = (block: Block): BlockSnapshot => ({
	blockId: block.blockId,
	element: block.element,
	isRoot: block.isRoot(),
	isText: block.isText(),
	isImage: block.isImage(),
	isHTML: block.isHTML(),
	isSVG: block.isSVG(),
	isLink: block.isLink(),
	isContainer: block.isContainer(),
	isVideo: block.isVideo(),
	isInput: block.isInput(),
	isRepeater: block.isRepeater(),
	isComponent: block.isExtendedFromComponent(),
	// This field is the component name, not a method.
	isChildOfComponent: Boolean(block.isChildOfComponent),
});

/** Returns `count` and `blockIds`. For one block, it also returns the block snapshot. */
const getSelection = () => {
	const blocks = blockController.getSelectedBlocks();
	const shared = { count: blocks.length, blockIds: blocks.map((block) => block.blockId) };
	return blocks.length === 1 ? { ...shared, ...getBlockSnapshot(blocks[0]) } : shared;
};

const getPage = () => {
	const active = usePageStore().activePage;
	if (!active) return null;

	return {
		route: active.route ?? "",
		isTemplate: Boolean(active.is_template),
		isStandard: Boolean(active.is_standard),
		published: Boolean(active.published),
	};
};

export const editorContext = computed<EditorContext>(() => {
	const builderStore = useBuilderStore();
	const canvasStore = useCanvasStore();

	return {
		selection: getSelection(),
		breakpoint: (canvasStore.activeCanvas?.activeBreakpoint ?? "desktop") as Breakpoint,
		editingMode: canvasStore.editingMode,
		readOnly: builderStore.readOnlyMode,
		isAIEnabled: builderStore.isAIEnabled,
		page: getPage(),
		site: {
			isDeveloperMode: Boolean(window.is_developer_mode),
			isFCSite: Boolean(window.is_fc_site),
		},
	};
});
