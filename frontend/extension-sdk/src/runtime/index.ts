/**
 * `frappe-builder-extension-sdk`: the object that an extension imports.
 *
 * - `connect.ts`: the handshake, and how the frame runs the extension code.
 * - `methods.ts`: `builder.toolbar`, `builder.context` and `builder.actions`.
 * - `slots.ts`: the five slots, and the slot that this frame runs.
 * - `actions.ts`: the action handlers that the host calls.
 *
 * The shell loads this file. The import map gives the same URL to the import
 * of the extension. So both use one module copy and one channel.
 */

import { getChannel, listenForHandshake } from "./connect";
import { actions, context, toolbar } from "./methods";
import { registerMain, use, type Mounter } from "./slots";

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

	/** A descriptor. Builder shows the button and sends the action back (Tier A). */
	toolbar,

	/** The editor snapshot. Read it one time, or name the fields to watch. */
	context,

	/** The functions of this extension. A descriptor names one. The host calls it. */
	actions,

	host: {
		/** The Builder version that runs this extension. An extension has its own release schedule. */
		info: () => getChannel().call<HostInfo>("host.info"),
	},
};

listenForHandshake();

export default builder;
