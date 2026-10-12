/**
 * The items that an extension adds to the editor UI, as one method table.
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
