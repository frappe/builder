/**
 * The items that an extension adds to the editor UI, as one method table.
 *
 * - `toolbarMethods.ts`, `contextMenuMethods.ts`, `propertiesMethods.ts`,
 *   `leftPanelMethods.ts`, `settingsMethods.ts`: one file for each surface.
 * - `controlSchema.ts`: changes a control from data into a right panel property.
 * - `actionMethods.ts`: the actions that a button or a menu item runs.
 * - `openMethods.ts`: what opens when a user opens an extension.
 * - `surfaceItems.ts`: the record keeping that each surface shares.
 *
 * To add a surface, add one import and one spread here.
 */

import type { MethodTable } from "../bridge/permissions";
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
