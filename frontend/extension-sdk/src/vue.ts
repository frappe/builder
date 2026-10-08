/**
 * `frappe-builder-extension-sdk/vue`: Vue helpers. They go in the bundle of the extension.
 * Import the SDK by its package name here. A relative import adds a second SDK copy with no port.
 */

import builder from "frappe-builder-extension-sdk";
import type { ContextField, EditorContext } from "frappe-builder-extension-sdk";
import { createApp, getCurrentScope, onScopeDispose, reactive, type Component } from "vue";

/** The value before the host answers. So `context.selection.count` shows zero and does not fail. */
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
 * The editor snapshot as a reactive object. The host sends only the named fields.
 * The subscription stops with the component.
 */
export const useBuilderContext = (fields: ContextField[]) => {
	const context = reactive(emptyContext());

	const pushed: Record<string, unknown> = {};
	const stop = builder.context.subscribe(fields, (next) => {
		Object.assign(pushed, next);
		Object.assign(context, next);
	});

	// A subscription does not send the current value. So ask for it.
	// If a push comes first, keep the push. This answer can be older.
	void builder.context.get().then((snapshot) => Object.assign(context, snapshot, pushed));

	// Outside a Vue scope, the subscription stops when the frame unloads.
	if (getCurrentScope()) onScopeDispose(stop);

	return context;
};

/** An action of this extension, as a function that a template can call. */
export const useAction = (name: string) => (context?: Record<string, unknown>) =>
	builder.actions.run(name, context);

/**
 * Mounts the `component()` of each slot. Register it one time in the entry: `builder.use(vueAdapter)`.
 * The props from the handshake become the root props.
 */
export const vueAdapter = (component: unknown, element: HTMLElement, props: Record<string, unknown> = {}) => {
	const app = createApp(component as Component, props);
	app.mount(element);
	return () => app.unmount();
};

/**
 * Makes a slot module from a component: `export const { mount } = defineSlot(Panel)`.
 * Use it when one slot mounts in its own way. Usually, use `vueAdapter`.
 */
export const defineSlot = (component: Component) => ({
	mount: (element: HTMLElement, props: Record<string, unknown> = {}) => {
		const app = createApp(component, props);
		app.mount(element);
		return () => app.unmount();
	},
});
