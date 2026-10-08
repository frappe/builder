/**
 * The one bridge of the editor. Only `index.ts` fills its method table.
 * Do not import a store here. The surface tests import this file and run without pinia.
 */

import { createExtensionBridge } from "./extensionBridge";

export const bridge = createExtensionBridge();
