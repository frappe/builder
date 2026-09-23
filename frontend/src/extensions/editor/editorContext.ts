/**
 * Builder's live state, reduced to what an extension may read.
 *
 * A computed, so the 23 context menu items that read it during one render share
 * one evaluation, and so milestone 5 can watch it rather than keep a second copy.
 *
 * Stores resolve inside the getter. A registry module must not import Vue SFC
 * scope, and resolving a store at import time would tie this
 * module to the order the editor loads in.
 */

import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { computed } from "vue";
import type { BlockFacts, Breakpoint, EditorContext } from "frappe-builder-extension-sdk/types";

/**
 * One block's own answers. Read from the block, not from `blockController`,
 * because the caller has already decided which block it means.
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
	// a string field holding the component name, not a method
	isChildOfComponent: Boolean(block.isChildOfComponent),
});

/**
 * No single block answers for an ambiguous selection, so only `count` and
 * `blockIds` survive one. `blockIds` is what an extension acts on when it wants
 * every selected block, and it is the only way to reach them once the per-block
 * fields go quiet.
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
