/**
 * `frappe-builder-extension-sdk`: the object that an extension imports.
 *
 * - `connect.ts`: the handshake, and how the frame runs the extension code.
 * - `methods.ts`: the `builder.<surface>` APIs.
 * - `slots.ts`: the five slots, and the slot that this frame runs.
 * - `actions.ts`: the action handlers that the host calls.
 * - `ui.ts`: toasts, dialogs and popovers from inside a frame.
 * - `resourceFetcher.ts`: sends frappe-ui resource requests through the bridge.
 *
 * The shell loads this file. The import map gives the same URL to the import
 * of the extension. So both use one module copy and one channel.
 */

import { getChannel, listenForHandshake } from "./connect";
import {
	actions,
	block,
	context,
	contextMenu,
	data,
	leftPanel,
	open,
	page,
	properties,
	schema,
	settings,
	state,
	toolbar,
	tokens,
} from "./methods";
import { resourceFetcher } from "./resourceFetcher";
import { registerMain, registerSlot, use, type Mounter, type SlotEntry } from "./slots";
import { ui } from "./ui";

export type HostInfo = { version: string; protocol: number };

const builder = {
	/**
	 * Startup code. It runs only in the hidden entry frame.
	 *
	 * Do not put registrations here. Every frame must read them.
	 * So they go at module scope.
	 */
	main: (handler: () => void) => registerMain(handler),

	/**
	 * Sets the adapter that mounts a component. Call it one time for each extension.
	 *
	 * `frappe-builder-extension-sdk/vue` exports `vueAdapter`. If there is no
	 * adapter, the module of each slot must export `mount(element, props)`.
	 */
	use: (adapter: Mounter) => use(adapter),

	/**
	 * The document that `ui.openDialog` opens. Builder does not send it to the host.
	 * A call opens a dialog. So this registration stays in the frame that made it.
	 */
	dialog: {
		register: (entry: SlotEntry) => registerSlot("dialog", entry),
	},

	/** The same, for the floating panel that `ui.openPopover` opens. */
	popover: {
		register: (entry: SlotEntry) => registerSlot("popover", entry),
	},

	/**
	 * What the Open button in the details pane of this extension opens. It is a
	 * popover, a dialog or the left panel tab of the extension. With no target,
	 * the pane shows no button.
	 */
	open,

	/** One tab. The entry frame registers it, and the host shows it (Tier C). */
	leftPanel,

	/** A descriptor. Builder shows the button and sends the action back (Tier A). */
	toolbar,

	/** A row in the block menu. The host checks its rule for the block under the cursor. */
	contextMenu,

	/** Tier B. A list that names Builder controls. The host shows them. */
	properties,

	/** One page in the settings dialog, and the document that it loads. */
	settings,

	/** The editor snapshot. Read it one time, or name the fields to watch. */
	context,

	/** One block, by the id from a menu row or from the snapshot. */
	block,

	/** The full tree, when one block is not sufficient. */
	page,

	/** A modal and a popover that a user can move. The host shows them around the document of this extension. */
	ui,

	/** The storage of this extension. It needs no permission, because Builder never reads it. */
	state,

	/** Real `Builder Token` rows. So they also reach the published site. */
	tokens,

	/**
	 * Site data. Each call needs the `data.access` permission.
	 *
	 * This file adds `fetcher`, not `methods.ts`. So `methods.ts` does not
	 * import the file that reads it. Connect it one time, in the entry:
	 *
	 * ```js
	 * import { setConfig } from "frappe-ui";
	 * setConfig("resourceFetcher", builder.data.fetcher);
	 * ```
	 *
	 * Then `createListResource` and `createDocumentResource` work as in any Frappe
	 * app. They get only what the user of the editor can get.
	 */
	data: { ...data, fetcher: resourceFetcher },

	/** The doctypes of this extension. Builder asks the user before it makes or removes a table. */
	schema,

	/** The functions of this extension. A descriptor names one. The host calls it. */
	actions,

	host: {
		/** The Builder version that runs this extension. An extension has its own release schedule. */
		info: () => getChannel().call<HostInfo>("host.info"),
	},
};

listenForHandshake();

export default builder;
