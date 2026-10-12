/**
 * Exports the extension method table and bridge API to the editor.
 */

import useBuilderStore from "@/stores/builderStore";
import { bridge } from "./bridge/bridge";
import { hostMethods } from "./bridge/hostMethods";
import { contextMethods } from "./context/contextMethods";
import { dataMethods } from "./data";
import { editorMethods } from "./editor";
import { surfaceMethods } from "./surfaces";

// the store loads on each call, not at import. So this code does not depend
// on the load order of the editor
bridge.setMethodTable(
	{ ...hostMethods, ...surfaceMethods, ...contextMethods, ...editorMethods, ...dataMethods },
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
