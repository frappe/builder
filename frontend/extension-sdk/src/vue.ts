/**
 * `frappe-builder-extension-sdk/vue` — the optional Vue layer.
 *
 * It ships in the author's bundle, not in `extension-sdk.js`, because it needs a
 * Vue runtime and the SDK ships none.
 */

import { createApp, type Component } from "vue";

/**
 * Mounts a component, for every slot this extension registers.
 *
 * ```js
 * builder.use(vueAdapter);
 * ```
 *
 * Register it once in the entry. The SDK then mounts the component a slot's
 * `component()` default-exports, and unmounts it when the frame goes away.
 * The props the handshake carries reach the component as its root props.
 */
export const vueAdapter = (component: unknown, element: HTMLElement, props: Record<string, unknown> = {}) => {
	const app = createApp(component as Component, props);
	app.mount(element);
	return () => app.unmount();
};

/**
 * A component as a slot module, for a slot that mounts itself.
 *
 * ```js
 * export const { mount } = defineSlot(Panel);
 * ```
 *
 * `vueAdapter` covers the ordinary case. Use this where one slot needs its own
 * mounting, or where the extension registers no adapter at all.
 */
export const defineSlot = (component: Component) => ({
	mount: (element: HTMLElement, props: Record<string, unknown> = {}) => {
		const app = createApp(component, props);
		app.mount(element);
		return () => app.unmount();
	},
});
