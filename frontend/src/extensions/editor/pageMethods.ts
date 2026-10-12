/**
 * The page: the tree that an extension reads.
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
