/**
 * Reading and writing one block.
 *
 * The context menu already hands an extension a `blockId`, and the snapshot
 * already carries `blockIds` for a multi-selection. Until now neither could be
 * resolved into anything. This is where an id becomes a block.
 *
 * An id arrives as a string from another realm, so the host resolves it against
 * the real tree and refuses anything that tree does not hold. Nothing here
 * trusts the frame beyond the shape of what it sent.
 *
 * Undo needs no help. `useCanvasHistory.ts:49` watches the root block deeply, so
 * a write made here is recorded as an undo step exactly like a write made by
 * Builder's own controls.
 */

import type Block from "@/block";
import useCanvasStore from "@/stores/canvasStore";
import { getBlockObject } from "@/utils/helpers";
import { nextTick } from "vue";
import type { MethodTable } from "../host/capabilities";
import { fields, oneOf, optionalText, refuse, text, wholeNumber } from "../params";
import type { Breakpoint } from "frappe-builder-extension-sdk/types";

const BREAKPOINTS = ["desktop", "tablet", "mobile"] as const;

/** A tag name, and nothing that could carry markup of its own. */
const ELEMENT_NAME = /^[a-z][a-z0-9-]*$/;

const findBlock = (blockId: string): Block => {
	const block = useCanvasStore().activeCanvas?.findBlock(blockId);
	if (!block) throw refuse(`This page holds no block named "${blockId}".`, "unknown_block");
	return block;
};

const namedBlock = (params: unknown) => findBlock(text(fields(params).blockId, "blockId"));

/**
 * The whole subtree, as a plain object.
 *
 * `getBlockObject` is the copy Builder already makes for its own clipboard and
 * history, so it strips the parent link and the component reference — the two
 * things that cannot cross a port — and it is the shape a block is stored in.
 * An extension therefore reads what it would write.
 */
const get = (params: unknown) => getBlockObject(namedBlock(params));

/** A record of strings, which is what an attribute map and a style map both are. */
const readMap = (value: unknown, name: string) => {
	if (value === undefined) return undefined;
	if (typeof value !== "object" || value === null || Array.isArray(value)) {
		throw refuse(`"${name}" must be an object.`, "invalid_params");
	}
	return value as Record<string, unknown>;
};

const readClasses = (value: unknown) => {
	if (value === undefined) return undefined;
	if (!Array.isArray(value) || value.some((entry) => typeof entry !== "string")) {
		throw refuse(`"classes" must be a list of strings.`, "invalid_params");
	}
	return value as string[];
};

/** `undefined` removes an attribute, the same way `removeAttribute` does. */
const writeAttributes = (block: Block, attributes: Record<string, unknown>) =>
	Object.entries(attributes).forEach(([attribute, value]) =>
		block.setAttribute(attribute, value === null ? undefined : optionalText(value, attribute)),
	);

/** `null` and `""` delete a style, which is `setStyle`'s own rule. */
const writeStyles = (block: Block, styles: Record<string, unknown>, breakpoint?: Breakpoint) =>
	Object.entries(styles).forEach(([style, value]) => {
		if (value !== null && typeof value !== "string" && typeof value !== "number") {
			throw refuse(`"styles.${style}" must be a string, a number or null.`, "invalid_params");
		}
		block.setStyle(style, value, breakpoint);
	});

/**
 * Every key is optional, and a patch naming none of them is a mistake worth
 * saying out loud rather than a write that quietly does nothing.
 *
 * A style lands on the breakpoint the user is looking at unless the patch names
 * one, because an extension writes without a canvas in front of it.
 */
const update = (params: unknown) => {
	const sent = fields(params);
	const block = namedBlock(params);

	const attributes = readMap(sent.attributes, "attributes");
	const styles = readMap(sent.styles, "styles");
	const classes = readClasses(sent.classes);
	const innerHTML = optionalText(sent.innerHTML, "innerHTML");
	const breakpoint =
		sent.breakpoint === undefined ? undefined : oneOf(sent.breakpoint, BREAKPOINTS, "breakpoint");

	if (!attributes && !styles && !classes && innerHTML === undefined) {
		throw refuse(`This patch changes nothing.`, "invalid_params");
	}

	if (attributes) writeAttributes(block, attributes);
	if (styles) writeStyles(block, styles, breakpoint);
	if (classes) block.classes = classes;
	if (innerHTML !== undefined) block.setInnerHTML(innerHTML);
};

/**
 * A tree is bounded, because the frame is the untrusted side. A message with no
 * ceiling on it is a message that costs the editor an unbounded amount of work.
 */
const MAX_NODES = 200;
const MAX_DEPTH = 20;

/**
 * One node, read and checked, with nothing added to the page yet.
 *
 * The whole tree becomes this before the first `addChild` runs. That is what
 * makes a refusal leave the page exactly as it was: a bad node at depth four
 * cannot half-build the three above it.
 */
type PlannedBlock = {
	element: string;
	key?: string;
	classes?: string[];
	innerHTML?: string;
	attributes?: Record<string, unknown>;
	styles?: Record<string, unknown>;
	children: PlannedBlock[];
};

const readChildren = (value: unknown) => {
	if (value === undefined) return [];
	if (!Array.isArray(value)) throw refuse(`"block.children" must be a list.`, "invalid_params");
	return value;
};

/**
 * The tree an extension sent, as something safe to build.
 *
 * A `key` is how the caller finds one node again — the submit button of a form
 * it just drew. It is the caller's own name for the node, so two nodes cannot
 * share one, and the host never reads it as anything but a label.
 */
const planTree = (value: unknown): PlannedBlock => {
	const keys = new Set<string>();
	let count = 0;

	const plan = (sent: unknown, depth: number): PlannedBlock => {
		if (depth > MAX_DEPTH) throw refuse(`A tree can be ${MAX_DEPTH} blocks deep.`, "invalid_params");
		if (++count > MAX_NODES) throw refuse(`A tree can hold ${MAX_NODES} blocks.`, "invalid_params");

		const wanted = fields(sent);
		const element = text(wanted.element, "block.element");
		if (!ELEMENT_NAME.test(element)) {
			throw refuse(`"${element}" is not an element name.`, "invalid_params");
		}

		const key = optionalText(wanted.key, "block.key");
		if (key && keys.has(key)) throw refuse(`Two blocks share the key "${key}".`, "invalid_params");
		if (key) keys.add(key);

		return {
			element,
			key,
			classes: readClasses(wanted.classes),
			innerHTML: optionalText(wanted.innerHTML, "block.innerHTML"),
			attributes: readMap(wanted.attributes, "block.attributes"),
			styles: readMap(wanted.styles, "block.styles"),
			children: readChildren(wanted.children).map((child) => plan(child, depth + 1)),
		};
	};

	return plan(value, 1);
};

/** Builds one planned node and everything under it, in the order it was sent. */
const mount = (
	parent: Block,
	planned: PlannedBlock,
	keys: Record<string, string>,
	breakpoint?: Breakpoint,
	index?: number,
): Block => {
	const block = parent.addChild(
		{ element: planned.element, classes: planned.classes, innerHTML: planned.innerHTML },
		index,
		false,
	);

	if (planned.attributes) writeAttributes(block, planned.attributes);
	if (planned.styles) writeStyles(block, planned.styles, breakpoint);
	if (planned.key) keys[planned.key] = block.blockId;

	planned.children.forEach((child) => mount(block, child, keys, breakpoint));
	return block;
};

/**
 * Builds the tree, and leaves the selection where it was.
 *
 * `addChild` calls `makeBlockEditable` for a text block whatever its `select`
 * argument says (`block.ts:595`), and that both selects the block and opens the
 * text editor on it. A form is mostly labels, so a tree of them ends with the
 * last label selected and in edit mode.
 *
 * The restore waits a tick because the selection does. `Block.selectBlock`
 * queues its work in `nextTick` (`block.ts:654`), so a synchronous restore runs
 * first and the label takes the selection back. Ours is queued after every one
 * the build queued, so it settles last.
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
 * A new block, or a whole tree of them, as a child of one the page already holds.
 *
 * A node carries its own `children`, so an extension that generates markup — a
 * form, a card, a table — draws it in one call. The answer holds the root's
 * `blockId`, and `keys` maps every `key` the caller named to the block it made.
 *
 * **One call is one act.** History records through a trailing 100 ms debounce
 * (`useCanvasHistory.ts:13`), so a tree built here is one undo step. Twenty
 * separate calls usually are too, but their boundary is the clock rather than
 * the call: an extension that awaits anything slow inside a loop splits its own
 * form across two steps. This does not.
 *
 * **Nothing is built while the tree is read.** A refused node leaves the page
 * untouched, rather than half a form nobody asked for.
 *
 * **The new block is not selected.** The selection is the user's, and an
 * extension writing to the page has no business taking it.
 */
const insert = (params: unknown) => {
	const sent = fields(params);
	const parent = findBlock(text(sent.parentId, "parentId"));
	const index = sent.index === undefined ? undefined : wholeNumber(sent.index, "index");
	const breakpoint =
		sent.breakpoint === undefined ? undefined : oneOf(sent.breakpoint, BREAKPOINTS, "breakpoint");

	const planned = planTree(sent.block);

	const keys: Record<string, string> = {};
	const inserted = keepingSelection(() => mount(parent, planned, keys, breakpoint, index));
	return { blockId: inserted.blockId, keys };
};

export const blockMethods: MethodTable = {
	"block.get": { needs: "block.read", run: get },
	// read-only is refused in the bridge, once, for every write capability
	"block.update": { needs: "block.update", run: update },
	// adding a block changes what the page is, not what one block holds, so it is
	// its own grant. A user reading an install list can tell the two apart
	"block.insert": { needs: "block.insert", run: insert },
};
