/**
 * The methods that read or change the state of the editor, as one method table.
 */

import type { MethodTable } from "../bridge/permissions";
import { blockMethods } from "./blockMethods";
import { pageMethods } from "./pageMethods";
import { stateMethods } from "./stateMethods";
import { uiMethods } from "./uiMethods";

export const editorMethods: MethodTable = {
	...blockMethods,
	...pageMethods,
	...uiMethods,
	...stateMethods,
};
