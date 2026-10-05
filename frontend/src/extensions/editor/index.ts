/**
 * Every method an extension reads or writes the editor through, in one table.
 *
 * The counterpart of `surfaces/index.ts`. A surface adds something to Builder's
 * chrome. A file here reaches Builder's own state, so each one holds a real
 * permission rather than the `null` most surfaces carry.
 */

import type { MethodTable } from "../host/permissions";
import { contextMethods } from "./contextMethods";

export const editorMethods: MethodTable = {
	...contextMethods,
};
