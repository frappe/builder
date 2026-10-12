/** `builder.block`, `builder.page` and `builder.state`. */

import { call } from "./call";

export type BlockPatch = {
	attributes?: Record<string, string | null>;
	/** Writes to the breakpoint that the user sees, unless `breakpoint` names a different one. */
	styles?: Record<string, string | number | null>;
	classes?: string[];
	innerHTML?: string;
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
export type NewBlock = {
	element: string;
	attributes?: Record<string, string | null>;
	styles?: Record<string, string | number | null>;
	classes?: string[];
	innerHTML?: string;
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
};

export const state = {
	/** All the values that this extension stored for this user. A dev extension stores them in the browser. */
	get: () => call("state.get") as Promise<Record<string, unknown>>,
	/** Merges at the top level. It never removes a key that the patch does not name. */
	set: (state: Record<string, unknown>) => call("state.set", { state }),
	unset: (key: string) => call("state.unset", { key }),
};
