/**
 * `frappe-builder-extension-sdk/vue` — the optional Vue layer.
 *
 * It ships in the author's bundle, not in `extension-sdk.js`, because it needs a
 * Vue runtime and the SDK ships none. That is also why it imports the SDK by its
 * bare specifier and never by a relative path: a relative import would put a
 * second copy of `connect.ts` in the author's bundle, holding no port and no
 * channel, and every call through it would throw.
 */

import builder from "frappe-builder-extension-sdk";
import type { ContextField, EditorContext } from "frappe-builder-extension-sdk";
import { createApp, getCurrentScope, onScopeDispose, reactive, type Component } from "vue";

/**
 * What a template reads before the host has answered.
 *
 * The host answers `context.get` over a port, so the first paint happens before
 * any value arrives. A shape means `context.selection.count` renders zero rather
 * than throwing, and every field is replaced as soon as the answer lands.
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
 * Names the fields it wants, so the host sends nothing else and only when one of
 * them moves. The subscription stops with the component that opened it.
 */
export const useBuilderContext = (fields: ContextField[]) => {
	const context = reactive(emptyContext());

	const pushed: Record<string, unknown> = {};
	const stop = builder.context.subscribe(fields, (next) => {
		Object.assign(pushed, next);
		Object.assign(context, next);
	});

	// a subscription counts the current snapshot as already sent, so the host
	// pushes nothing until a field moves and the first value has to be asked for.
	// A push that landed first wins: this answer was asked for earlier and may be
	// older than it
	void builder.context.get().then((snapshot) => Object.assign(context, snapshot, pushed));

	// outside a Vue scope there is nothing to dispose this subscription; it stops when the extension frame unloads.
	if (getCurrentScope()) onScopeDispose(stop);

	return context;
};

/** One of this extension's own actions, as a function a template can call. */
export const useAction = (name: string) => (context?: Record<string, unknown>) =>
	builder.actions.run(name, context);

/**
 * Mounts a component, for every slot this extension registers.
 *
 * ```js
 * builder.use(vueAdapter);
 * ```
 *
 * Register it once in the entry. The SDK then mounts the component a slot's
 * `component()` default-exports, and unmounts it when the frame goes away.
 * `props` reaches the component as its root props, so a dialog opened with
 * `ui.openDialog({ props })` reads them as ordinary props.
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
