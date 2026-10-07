/**
 * The methods that read or change site records and doctypes, as one method table.
 *
 * - `documentMethods.ts`: read, add, change and remove documents.
 * - `schemaMethods.ts`: add, read and remove the doctypes of an extension.
 * - `confirmations.ts`: the questions that Builder asks before an act that cannot be undone.
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
