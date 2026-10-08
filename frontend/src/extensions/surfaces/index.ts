/**
 * The items that an extension adds to the editor UI, as one method table.
 *
 * - `toolbarMethods.ts`: toolbar buttons.
 * - `actionMethods.ts`: the actions that a button or a menu item runs.
 * - `surfaceItems.ts`: the record keeping that each surface shares.
 *
 * To add a surface, add one import and one spread here.
 */

import type { MethodTable } from "../bridge/permissions";
import { actionMethods } from "./actionMethods";
import { toolbarMethods } from "./toolbarMethods";

export const surfaceMethods: MethodTable = {
	...toolbarMethods,
	...actionMethods,
};
