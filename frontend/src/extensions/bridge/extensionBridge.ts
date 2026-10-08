/**
 * Keeps the live state of each extension: its frames, its message budget and its cleanups.
 * A test makes its own bridge with its own method table.
 */

import { ChannelCallError, unknownMethod, type RequestHandler, type PortChannel } from "frappe-builder-extension-sdk/transport";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { assertGranted, assertWritable, type MethodTable } from "./permissions";
import { createBudget, type Budget } from "./rateLimit";

const overBudget = (extension: string) =>
	new ChannelCallError({ message: `"${extension}" is sending too many messages.`, code: "rate_limited" });

/** The caller gives `isReadOnly`. So this file does not import a store. */
export type BridgeOptions = { isReadOnly?: () => boolean };

export const createExtensionBridge = (methods: MethodTable = {}, options: BridgeOptions = {}) => {
	let { isReadOnly } = options;
	// A Map finds only the registered methods, not "constructor" from the prototype.
	const methodTable = new Map(Object.entries(methods));
	// Each key is the name of an extension.
	const entryChannels = new Map<string, PortChannel>();
	// All live frames of an extension. A context push goes to each frame.
	// An action goes only to the entry channel.
	const channels = new Map<string, Set<PortChannel>>();
	const budgets = new Map<string, Budget>();
	const cleanups = new Map<string, Array<() => void>>();

	// All frames of one extension share one budget.
	const budgetFor = (extension: string) => {
		const known = budgets.get(extension);
		if (known) return known;

		const budget = createBudget(extension);
		budgets.set(extension, budget);
		return budget;
	};

	/** The first frame that connects is the entry frame. Other frames open after `main.js` adds a surface. */
	const connect = (extension: string, channel: PortChannel) => {
		if (!entryChannels.has(extension)) entryChannels.set(extension, channel);

		const live = channels.get(extension) ?? new Set<PortChannel>();
		channels.set(extension, live);
		live.add(channel);
	};

	/** Compares the channel, not the name. So a frame that connects again keeps its new channel. */
	const disconnect = (extension: string, channel: PortChannel) => {
		if (entryChannels.get(extension) === channel) entryChannels.delete(extension);
		channels.get(extension)?.delete(channel);
	};

	const getEntryChannel = (extension: string) => entryChannels.get(extension);

	/** Returns a copy of the live frames. So a disconnect during a push is safe. */
	const getChannels = (extension: string) => [...(channels.get(extension) ?? [])];

	/**
	 * Makes a request handler for one frame. A frame cannot name a different extension.
	 * Do not cache the handler. A new record can have new permissions.
	 */
	const requestHandlerFor =
		(extension: InstalledExtension): RequestHandler =>
		(method, params) => {
			// The budget check is first. Calls to unknown methods also count.
			if (!budgetFor(extension.name).take()) throw overBudget(extension.name);

			const entry = methodTable.get(method);
			if (!entry) throw unknownMethod(method);

			assertGranted(extension, method, entry.needs);
			if (isReadOnly?.()) assertWritable(extension, method, entry.needs);
			return entry.run(params, extension);
		};

	/** Fills the method table after the bridge exists. Call it one time only. */
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

	/** Runs the cleanups and closes the frames. It does not wait for the extension. */
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
