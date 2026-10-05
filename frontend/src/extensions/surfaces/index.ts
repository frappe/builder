/**
 * Every method a surface answers, in one table.
 *
 * Each surface file owns its registry, its validation and its descriptor.
 * `surfaceItems.ts` holds the bookkeeping they share. This file only gathers
 * them, so adding a surface is one import and one spread.
 */

import type { MethodTable } from "../host/permissions";
import { actionMethods } from "./actionMethods";
import { toolbarMethods } from "./toolbarMethods";

export const surfaceMethods: MethodTable = {
	...toolbarMethods,
	...actionMethods,
};
