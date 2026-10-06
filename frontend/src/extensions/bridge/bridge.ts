/**
 * The one bridge the editor runs on.
 *
 * It lives here, apart from `index.ts`, so a surface can import `dispatcherFor`
 * to build a frame's props without importing the module that composes the
 * method table. The dependency then runs one way: index → surfaces → bridge.
 *
 * `index.ts` fills the table with `setMethodTable`, and is the only caller that may. It
 * supplies the read-only reader in the same call, because this file must import
 * no store: six surface tests import it, and they run without pinia.
 */

import { createExtensionBridge } from "./extensionBridge";

export const bridge = createExtensionBridge();
