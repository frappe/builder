/**
 * Every method an extension reaches site data through, in one table.
 *
 * The third table, after `surfaces/index.ts` and `editor/index.ts`. This one
 * sits apart from `editor/` because what it touches outlives the page: a block
 * write is undone with one keystroke, and a document write is not.
 */

import type { MethodTable } from "../host/capabilities";
import { documentMethods } from "./documentMethods";
import { grantMethods } from "./grants";
import { schemaMethods } from "./schemaMethods";

export const dataMethods: MethodTable = {
	...grantMethods,
	...documentMethods,
	...schemaMethods,
};
