/**
 * The data that the host gives about itself.
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
