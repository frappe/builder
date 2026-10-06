/**
 * The host side of extensions. This file makes the method table and exports
 * the bridge API to the editor.
 *
 * - `bridge/`: the gate for each call from a frame. Permissions, rate limit, parameter checks.
 * - `context/`: the editor snapshot, the `showWhen` rules, and the context methods.
 * - `surfaces/`: the items that an extension adds to the editor UI.
 * - `editor/`: the methods that read or change blocks, pages, tokens and state.
 * - `data/`: the methods that read or change site records and doctypes.
 * - `components/`: the frames, the dialogs and the popover that the runtime shows.
 * - `devExtension.ts`: the extension from a dev server, for this session.
 * - `permissionClasses.ts`: the words that a user sees for each permission.
 *
 * The installed list is a resource, so it is in `@/data/extensions.ts`.
 * This is a module, not a store, because registry modules import it.
 */

import useBuilderStore from "@/stores/builderStore";
import { dataMethods } from "./data";
import { bridge } from "./bridge/bridge";
import { hostMethods } from "./bridge/hostMethods";
import { contextMethods } from "./context/contextMethods";
import { editorMethods } from "./editor";
import { surfaceMethods } from "./surfaces";

// the store resolves on each call, never at import, so nothing here depends on
// the order the editor loads in
bridge.setMethodTable(
	{ ...hostMethods, ...surfaceMethods, ...contextMethods, ...editorMethods, ...dataMethods },
	{ isReadOnly: () => useBuilderStore().readOnlyMode },
);

export const {
	connect: connectExtension,
	disconnect: disconnectExtension,
	getEntryChannel,
	dispatcherFor,
	registerTeardown,
	teardown: teardownExtension,
} = bridge;
