/**
 * `frappe-builder-extension-sdk` — the object an extension imports.
 *
 * The shell loads this file, and the import map resolves the same URL for the
 * extension's own import, so both get one module instance and one channel.
 */

import { getChannel, listenForHandshake } from "./connect";
import { registerMain, use, type Mounter } from "./slots";

export type HostInfo = { version: string; protocol: number };

const builder = {
	/**
	 * Imperative startup work, in the hidden entry frame only.
	 *
	 * Registrations do not belong here. They are declarations, and every frame
	 * needs to read them, so they go at module scope.
	 */
	main: (handler: () => void) => registerMain(handler),

	/**
	 * Names the layer that mounts a component, once for this extension.
	 *
	 * `frappe-builder-extension-sdk/vue` exports `vueAdapter`. Without one, a
	 * slot's module has to export `mount(element, props)` itself.
	 */
	use: (adapter: Mounter) => use(adapter),

	host: {
		/** Which Builder this extension landed in. An extension ships on its own schedule. */
		info: () => getChannel().call<HostInfo>("host.info"),
	},
};

listenForHandshake();

export default builder;
