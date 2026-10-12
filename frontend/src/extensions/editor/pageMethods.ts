/**
 * The page: the tree that an extension reads.
 *
 * The snapshot does not have the tree on purpose. The tree is large and it
 * changes on each key press. So an extension asks for it. `block.get` gives
 * one node to an extension that needs only one.
 *
 * The tree comes from the canvas, not from `pageStore.pageBlocks`, for two
 * reasons. Undo replaces the root instance, so `pageBlocks` is old after the
 * first undo. Also, `block.get` and `block.update` find blocks in the canvas.
 * A different tree would give ids that those two methods cannot find.
 *
 * When the user edits a component, the canvas has that fragment, not the page.
 * So this returns the fragment. The other choice gives ids that an extension
 * cannot use. `context.editingMode` tells which tree it is.
 */

import useCanvasStore from "@/stores/canvasStore";
import { getBlockObject } from "@/utils/helpers";
import type { MethodTable } from "../bridge/permissions";
import { refuse } from "../bridge/params";

/**
 * A list, because Builder stores a page as a list. Today the list always has
 * one root.
 *
 * With no canvas, the call is refused. It does not return an empty list. So an
 * extension that calls before the editor is ready can tell this from an empty page.
 */
const getBlocks = () => {
	const root = useCanvasStore().activeCanvas?.getRootBlock();
	if (!root) throw refuse("No canvas is open.", "no_canvas");
	return [getBlockObject(root)];
};

export const pageMethods: MethodTable = {
	"page.getBlocks": { needs: null, run: getBlocks },
};
