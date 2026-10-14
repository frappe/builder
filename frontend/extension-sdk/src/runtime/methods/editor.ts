/** `builder.block`, `builder.page` and `builder.state`. */

import { call } from "./call";

/**
 * One binding of a block to page data. `key` names a value of the page data
 * script, or a field of the item when the block is inside a repeater.
 */
export type BlockDataKey = {
	key: string;
	/** What the value sets: the text (`key` with `property: "innerHTML"`), an attribute, or a style. */
	type?: "key" | "attribute" | "style";
	property?: string;
	/** Where the key is read. The default is "dataScript". */
	comesFrom?: "dataScript" | "props" | "componentData";
};

type StyleMap = Record<string, string | number | null>;

/** One prop of a block, as the Props panel keeps it. */
export type BlockProp = {
	label?: string;
	isDynamic?: boolean;
	isPassedDown?: boolean;
	comesFrom?: "dataScript" | "props" | "componentData" | null;
	value?: string | null;
	isStandard?: boolean;
	propOptions?: Record<string, unknown>;
};

/**
 * Every block field an extension can write. The names are the ones `block.get`
 * returns, so a block can be read, changed, and written back.
 *
 * A map merges, and `null` removes one key. A list, a name, or a flag replaces
 * the value. Builder's own bookkeeping, such as `blockId`, is not here, and
 * neither is a block client script: put page code in a `Builder Client Script`.
 */
export type BlockFields = {
	element?: string;
	attributes?: Record<string, string | null>;
	/** The "HTML Attributes" of the editor. */
	customAttributes?: Record<string, string | null>;
	classes?: string[];
	innerHTML?: string;
	/** The breakpoint that the user sees, unless `breakpoint` names one. */
	styles?: StyleMap;
	baseStyles?: StyleMap;
	tabletStyles?: StyleMap;
	mobileStyles?: StyleMap;
	/** The name in the layers panel. */
	blockName?: string;
	/** Repeats the children for each item of the list that `dataKey.key` names. Needs `dataKey`. */
	isRepeaterBlock?: boolean;
	/** The list of a repeater. `null` clears it. */
	dataKey?: BlockDataKey | null;
	/** Replaces the whole list. Each entry needs `key`, `type`, and `property`. */
	dynamicValues?: Array<Required<Pick<BlockDataKey, "key" | "type" | "property">> & Pick<BlockDataKey, "comesFrom">>;
	/** The block shows only when this key has a truthy value. `null` clears it. */
	visibilityCondition?: Pick<BlockDataKey, "key" | "comesFrom"> | null;
	/** Replaces the whole map. */
	props?: Record<string, BlockProp>;
};

export type BlockPatch = BlockFields & {
	/** The breakpoint of `styles`. */
	breakpoint?: "desktop" | "tablet" | "mobile";
};

export const block = {
	/** One block and its subtree, as a plain object. The id comes from the context or from a menu row. */
	get: (blockId: string) => call("block.get", { blockId }) as Promise<Record<string, unknown>>,
	/** Refused without `page.edit`. Also refused while the page is read-only. */
	update: (blockId: string, patch: BlockPatch) => call("block.update", { blockId, ...patch }),
	/**
	 * Adds a new block inside `parentId`. It goes at the end, unless `index` names a position.
	 *
	 * A block has its own `children`. So a full form or card is one call and one
	 * undo step. The host adds nothing until the full tree is valid. So a refusal
	 * does not change the page.
	 *
	 * Returns the `blockId` of the root, and `keys`. `keys` maps each `key` in the
	 * tree to its new block. The new blocks are not selected. The selection of
	 * the user does not change.
	 */
	insert: (parentId: string, block: NewBlock, index?: number) =>
		call("block.insert", { parentId, block, index }) as Promise<InsertedBlock>,
};

/** What `block.insert` adds. `element` is required. All other fields are optional. */
export type NewBlock = BlockFields & {
	element: string;
	/** The name that the caller gives this node. The answer maps it to a `blockId`. It must be unique in one call. */
	key?: string;
	children?: NewBlock[];
};

export type InsertedBlock = {
	/** The root of the blocks that this call made. */
	blockId: string;
	/** Each `key` in the tree, and its new block. Empty when the tree has no keys. */
	keys: Record<string, string>;
};

export const page = {
	/**
	 * The tree of the canvas, as a list of roots. A node has its own `children`.
	 * Go through them to reach each block.
	 *
	 * When the user edits a component, this returns that component. `block.get`
	 * and `block.update` can find only those ids. Read `context.editingMode` to
	 * know which tree you have.
	 */
	getBlocks: () => call("page.getBlocks") as Promise<Array<Record<string, unknown>>>,
	/**
	 * Shows a page in the editor, by its `Builder Page` name. It answers when the
	 * page has loaded, so a following call acts on that page.
	 */
	open: (name: string) => call("page.open", { name }),
	/**
	 * Sets the preview values of the open page, such as `{ slug: "hello-world" }`
	 * for a route `/blog/:slug`. The canvas then shows their data. They are
	 * editor state, not part of the page. Read them in `context.routeVariables`.
	 */
	setRouteVariables: (values: Record<string, string>) => call("page.setRouteVariables", { values }),
};

export const state = {
	/** All the values that this extension stored for this user. A dev extension stores them in the browser. */
	get: () => call("state.get") as Promise<Record<string, unknown>>,
	/** Merges at the top level. It never removes a key that the patch does not name. */
	set: (state: Record<string, unknown>) => call("state.set", { state }),
	unset: (key: string) => call("state.unset", { key }),
};
