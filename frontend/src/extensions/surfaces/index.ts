/**
 * All the methods of the surfaces, in one table.
 *
 * Each surface file owns its registry, its validation and its descriptor.
 * `surfaceItems.ts` has the shared record keeping. This file only collects the
 * tables. So a new surface needs one import and one spread.
 */

import type { MethodTable } from "../host/permissions";
import { actionMethods } from "./actionMethods";
import { toolbarMethods } from "./toolbarMethods";

export const surfaceMethods: MethodTable = {
	...toolbarMethods,
	...actionMethods,
};
