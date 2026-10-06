/**
 * The methods that read or change the state of the editor, as one method table.
 *
 * - `blockMethods.ts`: read, change, add and remove blocks.
 * - `pageMethods.ts`: page blocks and page scripts.
 * - `tokenMethods.ts`: design tokens.
 * - `stateMethods.ts`: the saved state of an extension, for each user.
 * - `uiMethods.ts`: toasts, dialogs and popovers.
 * - `frameSurface.ts`: the shared state of a dialog or a popover frame.
 *
 * Most methods here need a permission. Most surface methods do not.
 */

import type { MethodTable } from "../bridge/permissions";
import { blockMethods } from "./blockMethods";
import { pageMethods } from "./pageMethods";
import { stateMethods } from "./stateMethods";
import { tokenMethods } from "./tokenMethods";
import { uiMethods } from "./uiMethods";

export const editorMethods: MethodTable = {
	...blockMethods,
	...pageMethods,
	...uiMethods,
	...stateMethods,
	...tokenMethods,
};
