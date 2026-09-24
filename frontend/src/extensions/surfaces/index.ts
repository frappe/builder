/**
 * Every method a surface answers, in one table.
 *
 * Each surface file owns its registry, its validation and its descriptor.
 * `surfaceItems.ts` holds the bookkeeping they share. This file only gathers
 * them, so adding a surface is one import and one spread.
 */

import type { MethodTable } from "../host/capabilities";
import { actionMethods } from "./actionMethods";
import { contextMenuMethods } from "./contextMenuMethods";
import { leftPanelMethods } from "./leftPanelMethods";
import { openMethods } from "./openMethods";
import { propertyMethods } from "./propertiesMethods";
import { settingsMethods } from "./settingsMethods";
import { toolbarMethods } from "./toolbarMethods";

export const surfaceMethods: MethodTable = {
	...leftPanelMethods,
	...toolbarMethods,
	...contextMenuMethods,
	...propertyMethods,
	...settingsMethods,
	...actionMethods,
	...openMethods,
};
