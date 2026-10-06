/**
 * The data that the host gives about itself.
 *
 * This file is separate from `index.ts`. `index.ts` connects the parts and
 * imports the full editor through the surfaces. This file imports only a type.
 * So tests can use it.
 */

import { PROTOCOL_VERSION } from "frappe-builder-extension-sdk/types";
import type { MethodTable } from "./permissions";

/** An extension has its own release schedule. So it must know which Builder runs it. */
const getHostInfo = () => ({
	version: window.builder_version,
	protocol: PROTOCOL_VERSION,
});

export const hostMethods: MethodTable = {
	"host.info": { needs: null, run: getHostInfo },
};
