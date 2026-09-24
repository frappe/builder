/**
 * What the host answers about itself.
 *
 * Apart from `index.ts`, which is wiring and imports the whole editor through
 * the surfaces. This file imports nothing but a type, so it stays testable.
 */

import { PROTOCOL_VERSION } from "frappe-builder-extension-sdk/types";
import type { MethodTable } from "./capabilities";

/** An extension ships on its own schedule, so it needs to know where it landed. */
const getHostInfo = () => ({
	version: window.builder_version,
	protocol: PROTOCOL_VERSION,
});

export const hostMethods: MethodTable = {
	"host.info": { needs: null, run: getHostInfo },
};
