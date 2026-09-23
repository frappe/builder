/**
 * The one owner of an extension's live state: its frames, its message budget,
 * and the cleanup list teardown walks.
 *
 * A factory rather than a module: `index.ts` holds the one instance the editor
 * runs on, and a test builds its own with its own method table.
 */

import { ChannelCallError, unknownMethod, type Dispatcher, type PortChannel } from "frappe-builder-extension-sdk/transport";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { assertGranted, assertWritable, type MethodTable } from "./capabilities";
import { createBudget, type Budget } from "./rateLimit";

const overBudget = (extension: string) =>
	new ChannelCallError({ message: `"${extension}" is sending too many messages.`, code: "rate_limited" });

/**
 * `isReadOnly` is injected rather than imported, so no module on the way to this
 * factory has to import a store. `index.ts` supplies it with the method table,
 * because it is the one file that already imports the whole editor.
 */
export type BridgeOptions = { isReadOnly?: () => boolean };

export const createExtensionBridge = (methods: MethodTable = {}, options: BridgeOptions = {}) => {
	let { isReadOnly } = options;
	// Look up only registered methods. Object properties such as "constructor"
	// are inherited from the prototype and are not valid HostMethods.
	const methodTable = new Map(Object.entries(methods));
	// Extension keys throughout this bridge are InstalledExtension.name values.
	const entryChannels = new Map<string, PortChannel>();
	// every live frame of an extension, because a context push has more than one
	// destination. The entry channel above stays separate: it is the one frame an
	// action must reach, and it is chosen by arrival order rather than by liveness
	const channels = new Map<string, Set<PortChannel>>();
	const budgets = new Map<string, Budget>();
	const cleanups = new Map<string, Array<() => void>>();

	// keyed by extension, not by frame: every frame of one extension shares one budget
	const budgetFor = (extension: string) => {
		const known = budgets.get(extension);
		if (known) return known;

		const budget = createBudget(extension);
		budgets.set(extension, budget);
		return budget;
	};

	/**
	 * The first frame of an extension to connect is always its entry frame, because
	 * no UI frame can exist before `main.js` has registered anything.
	 */
	const connect = (extension: string, channel: PortChannel) => {
		if (!entryChannels.has(extension)) entryChannels.set(extension, channel);

		const live = channels.get(extension) ?? new Set<PortChannel>();
		channels.set(extension, live);
		live.add(channel);
	};

	/** Identity, not name: a reconnecting frame must not delete its own replacement. */
	const disconnect = (extension: string, channel: PortChannel) => {
		if (entryChannels.get(extension) === channel) entryChannels.delete(extension);
		channels.get(extension)?.delete(channel);
	};

	const getEntryChannel = (extension: string) => entryChannels.get(extension);

	/** Every frame the host can push to. A copy, so a disconnect mid-push is safe. */
	const getChannels = (extension: string) => [...(channels.get(extension) ?? [])];

	/**
	 * One dispatcher per frame, closed over the record it was handed, so a frame
	 * never names the extension it speaks for and cannot borrow another's grants.
	 *
	 * Not memoized: a refetched record carries fresh grants, and a cached
	 * dispatcher would keep answering with the old ones.
	 */
	const dispatcherFor =
		(extension: InstalledExtension): Dispatcher =>
		(method, params) => {
			// cheapest check first, and a flood of unknown methods is still a flood
			if (!budgetFor(extension.name).take()) throw overBudget(extension.name);

			const entry = methodTable.get(method);
			if (!entry) throw unknownMethod(method);

			assertGranted(extension, method, entry.needs);
			if (isReadOnly?.()) assertWritable(extension, method, entry.needs);
			return entry.run(params, extension);
		};

	/**
	 * Fills the method table after construction, so a surface can import the bridge for
	 * `dispatcherFor` without the bridge importing the surface back. Once only:
	 * a second call would give the method list two owners.
	 */
	const setMethodTable = (added: MethodTable, settings: BridgeOptions = {}) => {
		if (methodTable.size) throw new Error("The extension method table is already defined");
		Object.entries(added).forEach(([method, entry]) => methodTable.set(method, entry));
		isReadOnly = settings.isReadOnly ?? isReadOnly;
	};

	/** Milestone 4 records every cleanup the bridge needs when an extension leaves. */
	const registerTeardown = (extensionName: string, cleanup: () => void) => {
		const forExtension = cleanups.get(extensionName) ?? [];
		cleanups.set(extensionName, forExtension);
		forExtension.push(cleanup);
	};

	/**
	 * The bridge does not wait for a disabled or uninstalled extension to clean up
	 * after itself, because its frames may never run again.
	 */
	const teardown = (extensionName: string) => {
		cleanups.get(extensionName)?.forEach((cleanup) => cleanup());
		cleanups.delete(extensionName);
		entryChannels.get(extensionName)?.close();
		entryChannels.delete(extensionName);
		channels.delete(extensionName);
		budgets.delete(extensionName);
	};

	return { connect, disconnect, getEntryChannel, getChannels, setMethodTable, dispatcherFor, registerTeardown, teardown };
};

export type ExtensionBridge = ReturnType<typeof createExtensionBridge>;
