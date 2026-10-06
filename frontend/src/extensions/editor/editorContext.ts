/**
 * The live state of Builder, with only the fields that an extension can read.
 *
 * It is a computed. So the 23 context menu items that read it in one render
 * share one result. Also, `contextMethods.ts` can watch it and keep no second copy.
 *
 * The getter gets the stores. A registry module must not import Vue SFC scope.
 * A store that loads at import time makes this module depend on the load order
 * of the editor.
 */

import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import type { BlockFacts, Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/**
 * The facts about one block. They come from the block, not from
 * `blockController`, because the caller already chose the block.
 */
export const factsFor = (block: Block): BlockFacts => ({
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
 * When more than one block is selected, no one block gives the facts. So
 * only `count` and `blockIds` stay. An extension uses `blockIds` to act on all
 * selected blocks. When the fields for one block are empty, `blockIds` is the
 * only way to get the blocks.
 */
const getSelection = () => {
	const blocks = blockController.getSelectedBlocks();
	const shared = { count: blocks.length, blockIds: blocks.map((block) => block.blockId) };
	return blocks.length === 1 ? { ...shared, ...factsFor(blocks[0]) } : shared;
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
