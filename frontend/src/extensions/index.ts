/**
 * The host side of extensions. This file makes the method table and exports the bridge API.
 * The list of installations is in `@/data/extensions.ts`.
 */

import useBuilderStore from "@/stores/builderStore";
import { bridge } from "./bridge/bridge";
import { hostMethods } from "./bridge/hostMethods";
import { contextMethods } from "./context/contextMethods";
import { surfaceMethods } from "./surfaces";

// Get the store on each call, not at import. So the load order does not matter.
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
