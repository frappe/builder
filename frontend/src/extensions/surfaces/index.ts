/**
 * The methods for the items that an extension adds to the editor UI.
 * To add a surface, add one import and one spread here.
 */

import type { MethodTable } from "../bridge/permissions";
import { actionMethods } from "./actionMethods";
import { toolbarMethods } from "./toolbarMethods";

export const surfaceMethods: MethodTable = {
	...toolbarMethods,
	...actionMethods,
};
