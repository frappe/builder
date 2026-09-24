/**
 * Every method an extension reads or writes the editor through, in one table.
 *
 * The counterpart of `surfaces/index.ts`. A surface adds something to Builder's
 * chrome. A file here reaches Builder's own state, so each one holds a real
 * capability rather than the `null` most surfaces carry.
 */

import type { MethodTable } from "../host/capabilities";
import { blockMethods } from "./blockMethods";
import { contextMethods } from "./contextMethods";
import { pageMethods } from "./pageMethods";
import { stateMethods } from "./stateMethods";
import { tokenMethods } from "./tokenMethods";
import { uiMethods } from "./uiMethods";

export const editorMethods: MethodTable = {
	...contextMethods,
	...blockMethods,
	...pageMethods,
	...uiMethods,
	...stateMethods,
	...tokenMethods,
};
