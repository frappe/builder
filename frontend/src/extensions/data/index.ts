/**
 * The methods that read or change site records, as one method table.
 *
 * - `documentMethods.ts`: read, add, change and remove documents.
 * - `schemaMethods.ts`: make, change and remove the doctypes of an extension.
 *
 * Design tokens and client scripts are documents too (`Builder Token` and
 * `Builder Client Script`). So an extension changes them with these methods.
 *
 * This folder is separate from `editor/`. A user can undo a block change.
 * A user cannot undo a document change.
 */

import type { MethodTable } from "../bridge/permissions";
import { documentMethods } from "./documentMethods";
import { schemaMethods } from "./schemaMethods";

export const dataMethods: MethodTable = {
	...documentMethods,
	...schemaMethods,
};
