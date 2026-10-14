/**
 * The live state of Builder, with only the fields that an extension can read.
 */

import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import type { BlockSnapshot, Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/**
 * A snapshot of one block. It comes from the block, not from
 * `blockController`, because the caller already chose the block.
 */
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
	// a string field with the component name. It is not a method
	isChildOfComponent: Boolean(block.isChildOfComponent),
});

/**
 * When more than one block is selected, no one block gives a snapshot. So
 * only `count` and `blockIds` stay. An extension uses `blockIds` to act on all
 * selected blocks. When the fields for one block are empty, `blockIds` is the
 * only way to get the blocks.
 */
const getSelection = () => {
	const blocks = blockController.getSelectedBlocks();
	const shared = { count: blocks.length, blockIds: blocks.map((block) => block.blockId) };
	return blocks.length === 1 ? { ...shared, ...getBlockSnapshot(blocks[0]) } : shared;
};

const getPage = () => {
	const active = usePageStore().activePage;
	if (!active) return null;

	return {
		name: active.name,
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
