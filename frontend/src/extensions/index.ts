/**
 * The one place where the editor keeps its live extensions.
 *
 * It is a module, not a store. Registry code uses it, and a registry module
 * must not import Vue SFC scope. The install list is a resource. It is in
 * `@/data` with the other resources.
 *
 * The bridge is in `host/bridge.ts`. So a surface can import the bridge and
 * not import this file. This file makes the method table. So the bridge
 * never knows what a surface is.
 */

import useBuilderStore from "@/stores/builderStore";
import { editorMethods } from "./editor";
import { bridge } from "./host/bridge";
import { hostMethods } from "./host/hostMethods";
import { surfaceMethods } from "./surfaces";

// the store loads on each call, not at import. So this code does not depend
// on the load order of the editor
bridge.setMethodTable(
	{ ...hostMethods, ...surfaceMethods, ...editorMethods },
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
