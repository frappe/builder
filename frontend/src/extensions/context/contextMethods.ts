/**
 * The editor snapshot. An extension reads it one time, or gets a push when it changes.
 *
 * A push is the only message that the host sends without a request. All other
 * methods answer a request. So the message budget in `requestHandlerFor` covers them.
 *
 * A push goes through `channel.emit`. No budget applies to it, and none must.
 * A push comes from the user, not from a bad extension. If the push used the
 * request budget, a busy canvas could make the calls of the extension fail.
 * The throttle is the limit.
 *
 * There is one subscription for each extension. One watcher on `editorContext`
 * serves all of them. The snapshot is one computed. With one watcher for each
 * subscription, each change would compute the same value for each extension.
 */

import { useThrottleFn } from "@vueuse/core";
import { watch } from "vue";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import { fields as asFields, oneOf, refuse } from "../bridge/params";
import type { EditorContext, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { editorContext } from "./editorContext";

/** The keys of the snapshot. An extension can name only these fields. */
const CONTEXT_FIELDS = [
	"selection",
	"breakpoint",
	"editingMode",
	"readOnly",
	"isAIEnabled",
	"page",
	"site",
] as const;

type ContextField = (typeof CONTEXT_FIELDS)[number];

/**
 * With this delay, a drag across the canvas sends only a few messages.
 * The delay is too short for a user to see.
 */
const THROTTLE_MS = 100;

type Subscription = {
	fields: Set<ContextField>;
	/** The last sent value of each field, as JSON. */
	sent: Map<ContextField, string>;
	push: () => void;
};

const subscriptions = new Map<string, Subscription>();

/**
 * The first subscription makes the watcher. Module scope does not.
 *
 * `watch` reads its source one time when it starts. The getter of
 * `editorContext` gets the pinia stores. So a module that makes the watcher
 * at load time needs pinia. With this approach, tests can import this module
 * without pinia. Also, the watcher costs nothing in a session with no
 * subscription. Most sessions have none.
 */
let stopWatching: (() => void) | null = null;

const readFields = (params: unknown): ContextField[] => {
	const sent = asFields(params).fields;
	if (!Array.isArray(sent) || !sent.length) {
		throw refuse(`"fields" must be a non-empty list.`, "invalid_params");
	}
	return sent.map((field) => oneOf(field, CONTEXT_FIELDS, "fields"));
};

/**
 * Sends only the subscribed fields, and only when one of them changed.
 *
 * Each field decides if a push is necessary. But the payload has all the
 * subscribed fields. So a handler can destructure them without a check for
 * each field. With a partial payload, `({ selection }) => selection.count`
 * failed in the frame when a different field changed alone.
 */
const changedSince = (subscription: Subscription, context: EditorContext) => {
	let moved = false;
	const payload: Record<string, unknown> = {};
	subscription.fields.forEach((field) => {
		const value = context[field];
		const encoded = JSON.stringify(value);
		moved ||= encoded !== subscription.sent.get(field);
		subscription.sent.set(field, encoded);
		payload[field] = value;
	});
	return moved ? payload : null;
};

/**
 * Marks the current value of these fields as sent. So "changed" means changed
 * after the field was subscribed. Only new fields: a field that is already
 * subscribed can have a change that waits for the throttle.
 */
const remember = (subscription: Subscription, fields: ContextField[]) =>
	fields.forEach((field) => subscription.sent.set(field, JSON.stringify(editorContext.value[field])));

/**
 * Sends to each frame of the extension. A panel and the entry frame are two
 * parts of one extension. The handler can be in either frame. A frame with no
 * listener ignores the message. Only its listener list knows this.
 */
const send = (extension: string) => {
	const subscription = subscriptions.get(extension);
	if (!subscription) return;

	const payload = changedSince(subscription, editorContext.value);
	if (!payload) return;
	bridge.getChannels(extension).forEach((channel) => channel.emit("context", payload));
};

const forget = (extension: string) => {
	subscriptions.delete(extension);
	if (subscriptions.size) return;
	stopWatching?.();
	stopWatching = null;
};

/**
 * A second call adds its fields. It does not replace the first fields. All
 * handlers in a frame listen to the same `context` event. A replacement would
 * stop the first handler, with no message.
 */
const subscribe = (params: unknown, extension: InstalledExtension) => {
	const wanted = readFields(params);
	const known = subscriptions.get(extension.name);
	if (known) {
		const added = wanted.filter((field) => !known.fields.has(field));
		added.forEach((field) => known.fields.add(field));
		remember(known, added);
		return;
	}

	const subscription: Subscription = {
		fields: new Set(wanted),
		sent: new Map(),
		push: useThrottleFn(() => send(extension.name), THROTTLE_MS, true),
	};
	remember(subscription, wanted);
	subscriptions.set(extension.name, subscription);
	bridge.registerTeardown(extension.name, () => forget(extension.name));

	// no first push. At startup, the extension uses `context.get`. So the watcher waits for a change
	stopWatching ??= watch(editorContext, () => subscriptions.forEach((entry) => entry.push()));
};

export const contextMethods: MethodTable = {
	"context.get": { needs: null, run: () => editorContext.value },
	"context.subscribe": { needs: null, run: subscribe },
};
