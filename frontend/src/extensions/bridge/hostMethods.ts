/** Methods that give data about the host. This file imports only types, so tests can use it. */

import { PROTOCOL_VERSION } from "frappe-builder-extension-sdk/types";
import type { MethodTable } from "./permissions";

/** Tells the extension which Builder version and protocol run it. */
const getHostInfo = () => ({
	version: window.builder_version,
	protocol: PROTOCOL_VERSION,
});

export const hostMethods: MethodTable = {
	"host.info": { needs: null, run: getHostInfo },
};
