/**
 * `frappe-builder-extension-sdk`: the object that an extension imports.
 * The frame and the extension get the same URL. So they share one module copy and one channel.
 */

import { getChannel, listenForHandshake } from "./connect";
import { actions, context, toolbar } from "./methods";
import { registerMain, use, type Mounter } from "./slots";

export type HostInfo = { version: string; protocol: number };

const builder = {
	/** Startup code. It runs only in the hidden entry frame. Put registrations at module scope. */
	main: (handler: () => void) => registerMain(handler),

	/**
	 * Sets the adapter that mounts a component. Call it one time.
	 * Without an adapter, each slot module must export `mount(element, props)`.
	 */
	use: (adapter: Mounter) => use(adapter),

	/** Adds toolbar buttons. Builder shows the button and runs the action. */
	toolbar,

	/** The editor snapshot. Read it one time, or subscribe to fields. */
	context,

	/** The functions of this extension. A descriptor names one, and the host calls it. */
	actions,

	host: {
		/** The Builder version that runs this extension. */
		info: () => getChannel().call<HostInfo>("host.info"),
	},
};

listenForHandshake();

export default builder;
