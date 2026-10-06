/**
 * `frappe-builder-extension-sdk/vue`: the optional Vue layer.
 *
 * This file goes in the bundle of the author, not in `extension-sdk.js`. It
 * needs a Vue runtime, and the SDK has none.
 *
 * For the same reason, it imports the SDK by its package name, not by a
 * relative path. A relative import puts a second copy of `connect.ts` in the
 * bundle of the author. That copy has no port and no channel. Each call
 * through it fails.
 */

import builder from "frappe-builder-extension-sdk";
import type { ContextField, EditorContext } from "frappe-builder-extension-sdk";
import { createApp, getCurrentScope, onScopeDispose, reactive, type Component } from "vue";

/**
 * The value that a template reads before the host answers.
 *
 * The host answers `context.get` through a port. So the first paint occurs
 * before a value comes. With this shape, `context.selection.count` shows zero.
 * It does not fail. Each field changes when the answer comes.
 */
const emptyContext = (): EditorContext => ({
	selection: { count: 0, blockIds: [] },
	breakpoint: "desktop",
	editingMode: "page",
	readOnly: false,
	isAIEnabled: false,
	page: null,
	site: { isDeveloperMode: false, isFCSite: false },
});

/**
 * The editor snapshot, as a reactive object that follows the editor.
 *
 * It names the fields that it needs. The host sends only these fields, and only
 * when one of them changes. The subscription stops with the component that started it.
 */
export const useBuilderContext = (fields: ContextField[]) => {
	const context = reactive(emptyContext());

	const pushed: Record<string, unknown> = {};
	const stop = builder.context.subscribe(fields, (next) => {
		Object.assign(pushed, next);
		Object.assign(context, next);
	});

	// a subscription does not send the current snapshot. The host pushes only
	// when a field changes. So this code must ask for the first value.
	// If a push comes first, the push wins. This answer can be older than the push
	void builder.context.get().then((snapshot) => Object.assign(context, snapshot, pushed));

	// outside a Vue scope, nothing stops this subscription. It stops when the extension frame unloads
	if (getCurrentScope()) onScopeDispose(stop);

	return context;
};

/** An action of this extension, as a function that a template can call. */
export const useAction = (name: string) => (context?: Record<string, unknown>) =>
	builder.actions.run(name, context);

/**
 * Mounts a component for each slot that this extension registers.
 *
 * ```js
 * builder.use(vueAdapter);
 * ```
 *
 * Register it one time in the entry. The SDK then mounts the default export of
 * the `component()` of each slot. It unmounts the component when the frame closes.
 * The props from the handshake become the root props of the component.
 */
export const vueAdapter = (component: unknown, element: HTMLElement, props: Record<string, unknown> = {}) => {
	const app = createApp(component as Component, props);
	app.mount(element);
	return () => app.unmount();
};

/**
 * Makes a slot module from a component, for a slot that mounts itself.
 *
 * ```js
 * export const { mount } = defineSlot(Panel);
 * ```
 *
 * Usually, use `vueAdapter`. Use this function when one slot must mount in its
 * own way, or when the extension registers no adapter.
 */
export const defineSlot = (component: Component) => ({
	mount: (element: HTMLElement, props: Record<string, unknown> = {}) => {
		const app = createApp(component, props);
		app.mount(element);
		return () => app.unmount();
	},
});
