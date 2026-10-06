/**
 * All the methods that an extension uses to read or change the editor, in one table.
 *
 * This file is the pair of `surfaces/index.ts`. A surface adds an item to the
 * Builder UI. A file here reads or changes the state of Builder. So a method
 * here can need a permission. Most surfaces have `null`.
 */

import type { MethodTable } from "../host/permissions";
import { contextMethods } from "./contextMethods";

export const editorMethods: MethodTable = {
	...contextMethods,
};
