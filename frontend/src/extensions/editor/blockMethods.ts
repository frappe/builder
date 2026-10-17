/**
 * Reads and changes blocks.
 */

import Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { getBlockObject } from "@/utils/helpers";
import { nextTick } from "vue";
import type { MethodTable } from "../bridge/permissions";
import { fields, oneOf, optionalText, refuse, text, wholeNumber } from "../bridge/params";
import type { Breakpoint } from "frappe-builder-extension-sdk/types";
import { assertCanRepeat } from "./blockBindings";
import { readBlockFields, writeBlockFields, type BlockFields } from "./blockFields";
import { readElement } from "./safeMarkup";

const BREAKPOINTS = ["desktop", "tablet", "mobile"] as const;

const findBlock = (blockId: string): Block => {
	const block = useCanvasStore().activeCanvas?.findBlock(blockId);
	if (!block) throw refuse(`This page holds no block named "${blockId}".`, "unknown_block");
	return block;
};

const namedBlock = (params: unknown) => findBlock(text(fields(params).blockId, "blockId"));

/**
 * The full subtree, as a plain object.
 *
 * Builder already uses `getBlockObject` for its clipboard and history. It
 * removes the parent link and the component reference. These two cannot go
 * through a port. It is also the shape that Builder stores. So an extension
 * reads the same shape that it writes.
 */
const get = (params: unknown) => getBlockObject(namedBlock(params));

/**
 * Each key is optional. A patch with no keys is an error. It is better to
 * show the error than to do nothing.
 *
 * A style goes to the breakpoint that the user sees, unless the patch names a
 * breakpoint. An extension does not see the canvas.
 */
const readBreakpoint = (sent: Record<string, unknown>) =>
	sent.breakpoint === undefined ? undefined : oneOf(sent.breakpoint, BREAKPOINTS, "breakpoint");

/** A new tag must still hold the children the block has. The page root keeps its tag. */
const assertCanRetag = (changes: BlockFields, block: Block) => {
	if (changes.element === undefined) return;
	if (block.isRoot()) throw refuse("The page root keeps its element.", "invalid_params");
	const retagged = new Block({ element: changes.element as string });
	if (block.children.length && !retagged.canHaveChildren()) {
		throw refuse(`A <${changes.element}> block cannot hold the children this block has.`, "invalid_params");
	}
};

const update = (params: unknown) => {
	const sent = fields(params);
	const block = namedBlock(params);
	const changes = readBlockFields(sent, block.getElement() || "div", ["blockId", "breakpoint"]);
	if (!Object.keys(changes).length) throw refuse(`This patch changes nothing.`, "invalid_params");
	assertCanRetag(changes, block);
	assertCanRepeat(changes, block);
	writeBlockFields(block, changes, readBreakpoint(sent));
};

/**
 * A tree has a size limit, because the frame is not trusted. Without a limit,
 * one message could give the editor too much work.
 */
const MAX_NODES = 200;
const MAX_DEPTH = 20;

/**
 * One node, read and checked. Nothing is on the page yet.
 *
 * The full tree gets this form before the first `addChild` runs. So a refusal
 * does not change the page. A bad node at depth four cannot leave the three
 * nodes above it half built.
 */
type PlannedBlock = {
	element: string;
	key?: string;
	changes: BlockFields;
	children: PlannedBlock[];
};

/** The canvas keeps text, images and inputs as leaves. A child of one would not show. */
const assertCanHaveChildren = (block: Block) => {
	if (!block.canHaveChildren()) {
		throw refuse(`A <${block.getElement()}> block cannot have children.`, "invalid_params");
	}
};

const readChildren = (value: unknown) => {
	if (value === undefined) return [];
	if (!Array.isArray(value)) throw refuse(`"block.children" must be a list.`, "invalid_params");
	return value;
};

/**
 * The tree from an extension, in a form that is safe to build.
 *
 * The caller uses a `key` to find one node again, for example the submit
 * button of a new form. It is the name that the caller gives the node. So two
 * nodes cannot have the same key. The host reads it only as a label.
 */
const planTree = (value: unknown): PlannedBlock => {
	const keys = new Set<string>();
	let count = 0;

	const plan = (sent: unknown, depth: number): PlannedBlock => {
		if (depth > MAX_DEPTH) throw refuse(`A tree can be ${MAX_DEPTH} blocks deep.`, "invalid_params");
		if (++count > MAX_NODES) throw refuse(`A tree can hold ${MAX_NODES} blocks.`, "invalid_params");

		const wanted = fields(sent);
		const element = readElement(wanted.element, "block.element");

		const key = optionalText(wanted.key, "block.key");
		if (key && keys.has(key)) throw refuse(`Two blocks share the key "${key}".`, "invalid_params");
		if (key) keys.add(key);

		// `addChild` sets the tag, so the other fields are the changes
		const { element: _tag, ...changes } = readBlockFields(wanted, element, ["key", "children"], "block.");
		const children = readChildren(wanted.children);
		const draft = new Block({ element, innerHTML: changes.innerHTML as string | undefined });
		if (children.length) assertCanHaveChildren(draft);
		assertCanRepeat(changes, draft);

		return { element, key, changes, children: children.map((child) => plan(child, depth + 1)) };
	};

	return plan(value, 1);
};

/** Builds one planned node and all nodes below it, in the order that they came. */
const mount = (
	parent: Block,
	planned: PlannedBlock,
	keys: Record<string, string>,
	breakpoint?: Breakpoint,
	index?: number,
): Block => {
	const block = parent.addChild({ element: planned.element }, index, false);
	writeBlockFields(block, planned.changes, breakpoint);
	if (planned.key) keys[planned.key] = block.blockId;

	planned.children.forEach((child) => mount(block, child, keys, breakpoint));
	return block;
};

/**
 * Builds the tree, and does not change the selection.
 *
 * `addChild` calls `makeBlockEditable` for each text block, for any value of
 * `select` (see `block.ts`). That selects the block and opens the text editor.
 * A form has many labels. So without this, the last label is selected and in
 * edit mode.
 *
 * The restore waits one tick, because the selection also waits.
 * `Block.selectBlock` queues its work in `nextTick`. A synchronous restore
 * would run first, and then the label would take the selection back. This
 * restore is queued after all the others, so it runs last.
 */
const keepingSelection = <T>(build: () => T): T => {
	const store = useCanvasStore();
	const canvas = store.activeCanvas;
	const selected = [...(canvas?.selectedBlockIds ?? [])];
	const editable = store.editableBlock;

	const made = build();

	nextTick(() => {
		store.editableBlock = editable;
		canvas?.clearSelection();
		selected.forEach((blockId) => {
			const block = canvas?.findBlock(blockId);
			if (block) canvas?.toggleBlockSelection(block);
		});
	});
	return made;
};

/**
 * Adds a new block, or a full tree of blocks, as a child of a block on the page.
 *
 * A node has its own `children`. So an extension can add a form, a card or a
 * table in one call. The answer has the `blockId` of the root. `keys` maps each
 * `key` of the caller to its new block.
 *
 * **One call is one act.** History waits 100 ms after the last change before it
 * records (see `useCanvasHistory.ts`). So a tree from one call is one undo step.
 * Twenty separate calls are usually one step too, but the timer decides that,
 * not the calls. A slow loop can split one form into two steps. One call cannot.
 *
 * **Nothing is built while the tree is read.** A refused node does not change
 * the page. The page never gets half a form.
 *
 * **The new block is not selected.** The selection belongs to the user. An
 * extension that writes to the page must not change it.
 */
const insert = (params: unknown) => {
	const sent = fields(params);
	const parent = findBlock(text(sent.parentId, "parentId"));
	assertCanHaveChildren(parent);
	const index = sent.index === undefined ? undefined : wholeNumber(sent.index, "index");
	const breakpoint = readBreakpoint(sent);

	const planned = planTree(sent.block);

	const keys: Record<string, string> = {};
	const inserted = keepingSelection(() => mount(parent, planned, keys, breakpoint, index));
	return { blockId: inserted.blockId, keys };
};

export const blockMethods: MethodTable = {
	"block.get": { needs: null, run: get },
	// the bridge refuses each write permission in read-only mode, in one place
	"block.update": { needs: "page.edit", run: update },
	"block.insert": { needs: "page.edit", run: insert },
};
