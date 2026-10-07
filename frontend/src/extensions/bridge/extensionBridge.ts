/**
 * The one owner of the live state of an extension. This state is its frames,
 * its message budget and the cleanup list for teardown.
 *
 * It is a factory, not a module. `index.ts` keeps the one instance of the
 * editor. A test makes its own instance, with its own method table.
 */

import { ChannelCallError, unknownMethod, type RequestHandler, type PortChannel } from "frappe-builder-extension-sdk/transport";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { assertGranted, assertWritable, type MethodTable } from "./permissions";
import { createBudget, type Budget } from "./rateLimit";

const overBudget = (extension: string) =>
	new ChannelCallError({ message: `"${extension}" is sending too many messages.`, code: "rate_limited" });

/**
 * The caller gives `isReadOnly`. This file does not import it. So no module
 * that leads to this factory must import a store. `index.ts` gives it with the
 * method table. It is the one file that already imports the full editor.
 */
export type BridgeOptions = { isReadOnly?: () => boolean };

export const createExtensionBridge = (methods: MethodTable = {}, options: BridgeOptions = {}) => {
	let { isReadOnly } = options;
	// find only registered methods. Object properties such as "constructor"
	// come from the prototype. They are not valid HostMethods
	const methodTable = new Map(Object.entries(methods));
	// in this bridge, each extension key is an InstalledExtension.name value
	const entryChannels = new Map<string, PortChannel>();
	// all live frames of an extension, because a context push can go to more than
	// one frame. The entry channel above is separate. An action must go to that
	// frame. The bridge chooses it by connect order, not by which frames are live
	const channels = new Map<string, Set<PortChannel>>();
	const budgets = new Map<string, Budget>();
	const cleanups = new Map<string, Array<() => void>>();

	// the key is the extension, not the frame. All frames of one extension share one budget
	const budgetFor = (extension: string) => {
		const known = budgets.get(extension);
		if (known) return known;

		const budget = createBudget(extension);
		budgets.set(extension, budget);
		return budget;
	};

	/**
	 * The first frame of an extension to connect is always its entry frame.
	 * No UI frame can exist before `main.js` registers a surface.
	 */
	const connect = (extension: string, channel: PortChannel) => {
		if (!entryChannels.has(extension)) entryChannels.set(extension, channel);

		const live = channels.get(extension) ?? new Set<PortChannel>();
		channels.set(extension, live);
		live.add(channel);
	};

	/** Compares the channel, not the name. A frame that connects again must not remove its new channel. */
	const disconnect = (extension: string, channel: PortChannel) => {
		if (entryChannels.get(extension) === channel) entryChannels.delete(extension);
		channels.get(extension)?.delete(channel);
	};

	const getEntryChannel = (extension: string) => entryChannels.get(extension);

	/** All frames that the host can push to. It is a copy. So a disconnect during a push is safe. */
	const getChannels = (extension: string) => [...(channels.get(extension) ?? [])];

	/**
	 * One request handler for each frame. It keeps the record that it got. So a frame
	 * never names its extension, and it cannot use the permissions of a different extension.
	 *
	 * There is no cache. A new record can have new permissions. A cached
	 * request handler would keep the old permissions.
	 */
	const requestHandlerFor =
		(extension: InstalledExtension): RequestHandler =>
		(method, params) => {
			// the fastest check is first. Too many calls to unknown methods are also too many calls
			if (!budgetFor(extension.name).take()) throw overBudget(extension.name);

			const entry = methodTable.get(method);
			if (!entry) throw unknownMethod(method);

			assertGranted(extension, method, entry.needs);
			if (isReadOnly?.()) assertWritable(extension, method, entry.needs);
			return entry.run(params, extension);
		};

	/**
	 * Fills the method table after the bridge exists. So a surface can import the
	 * bridge for `requestHandlerFor`, and the bridge does not import the surface.
	 * Call it only one time. A second call would give the method list two owners.
	 */
	const setMethodTable = (added: MethodTable, settings: BridgeOptions = {}) => {
		if (methodTable.size) throw new Error("The extension method table is already defined");
		Object.entries(added).forEach(([method, entry]) => methodTable.set(method, entry));
		isReadOnly = settings.isReadOnly ?? isReadOnly;
	};

	/** Records a cleanup that the bridge runs when an extension stops. */
	const registerTeardown = (extensionName: string, cleanup: () => void) => {
		const forExtension = cleanups.get(extensionName) ?? [];
		cleanups.set(extensionName, forExtension);
		forExtension.push(cleanup);
	};

	/**
	 * The bridge does not wait for a disabled or removed extension to clean up.
	 * Its frames can stop and not run again.
	 */
	const teardown = (extensionName: string) => {
		cleanups.get(extensionName)?.forEach((cleanup) => cleanup());
		cleanups.delete(extensionName);
		entryChannels.get(extensionName)?.close();
		entryChannels.delete(extensionName);
		channels.delete(extensionName);
		budgets.delete(extensionName);
	};

	return { connect, disconnect, getEntryChannel, getChannels, setMethodTable, requestHandlerFor, registerTeardown, teardown };
};

export type ExtensionBridge = ReturnType<typeof createExtensionBridge>;
