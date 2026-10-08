/**
 * The host side of extensions. This file makes the method table and exports
 * the bridge API to the editor.
 *
 * - `bridge/`: the gate for each call from a frame. Permissions, rate limit, parameter checks.
 * - `context/`: the editor snapshot, the `showWhen` rules, and the context methods.
 * - `surfaces/`: the items that an extension adds to the editor UI.
 * - `components/`: the frames, and the dialog that loads a dev extension.
 * - `devExtension.ts`: the extension from a dev server, for this session.
 *
 * The installed list is a resource, so it is in `@/data/extensions.ts`.
 * This is a module, not a store, because registry modules import it.
 */

import useBuilderStore from "@/stores/builderStore";
import { bridge } from "./bridge/bridge";
import { hostMethods } from "./bridge/hostMethods";
import { contextMethods } from "./context/contextMethods";
import { surfaceMethods } from "./surfaces";

// the store loads on each call, not at import. So this code does not depend
// on the load order of the editor
bridge.setMethodTable(
	{ ...hostMethods, ...surfaceMethods, ...contextMethods },
	{ isReadOnly: () => useBuilderStore().readOnlyMode },
);

export const {
	connect: connectExtension,
	disconnect: disconnectExtension,
	getEntryChannel,
	requestHandlerFor,
	registerTeardown,
	teardown: teardownExtension,
} = bridge;
