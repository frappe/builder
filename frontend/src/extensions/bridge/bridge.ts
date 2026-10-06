/**
 * The one bridge of the editor.
 *
 * This file is separate from `index.ts`. So a surface can import
 * `dispatcherFor` for the props of a frame. It does not import the module that
 * makes the method table. The imports then go in one direction:
 * index → surfaces → bridge.
 *
 * Only `index.ts` fills the table, with `setMethodTable`. The same call gives
 * the read-only reader. This file must import no store. Six surface tests
 * import it, and they run without pinia.
 */

import { createExtensionBridge } from "./extensionBridge";

export const bridge = createExtensionBridge();
