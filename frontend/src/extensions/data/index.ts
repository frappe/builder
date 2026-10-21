/**
 * The methods that read or change site records, as one method table.
 */

import type { MethodTable } from "../bridge/permissions";
import { documentMethods } from "./documentMethods";
import { requestMethods } from "./requestMethods";
import { schemaMethods } from "./schemaMethods";

export const dataMethods: MethodTable = {
	...documentMethods,
	...requestMethods,
	...schemaMethods,
};
