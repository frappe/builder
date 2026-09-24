/**
 * The editor snapshot, read once or pushed as it changes.
 *
 * This is the first thing the host sends without being asked. Every other method
 * answers a request, so the message budget in `dispatcherFor` covers it. A push
 * goes out through `channel.emit`, which no budget guards and none should: a
 * push is the user moving the mouse, not the extension misbehaving. Charging it
 * to the extension's request budget would let a busy canvas make its own calls
 * fail. The throttle is the cap.
 *
 * One subscription per extension, and one watcher over `editorContext` for all
 * of them. The snapshot is one computed, so a watcher per subscription would
 * evaluate the same value once per extension on every change.
 */

import { useThrottleFn } from "@vueuse/core";
import { watch } from "vue";
import { bridge } from "../host/bridge";
import type { MethodTable } from "../host/capabilities";
import { fields as asFields, oneOf, refuse } from "../params";
import type { EditorContext, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { editorContext } from "./editorContext";

/** The snapshot's own keys. A field an extension names must be one of these. */
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
 * Long enough that a drag across the canvas coalesces into a handful of
 * messages, short enough that no user sees the delay.
 */
const THROTTLE_MS = 100;

type Subscription = {
	fields: Set<ContextField>;
	/** What each field looked like when it was last sent, as JSON. */
	sent: Map<ContextField, string>;
	push: () => void;
};

const subscriptions = new Map<string, Subscription>();

/**
 * Created on the first subscription, not at module scope.
 *
 * `watch` reads its source once when it is created, and `editorContext` resolves
 * pinia stores inside its getter. Creating it here keeps this module importable
 * without pinia, and costs nothing in the sessions where no extension subscribes
 * to anything — which is most of them.
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
 * Nothing outside the subscribed fields ever travels, and nothing travels at all
 * unless one of them moved.
 *
 * Whether to send is decided per field. What to send is not: the payload carries
 * every subscribed field, so a handler can destructure them without guarding
 * each one. A partial payload made `({ selection }) => selection.count` throw
 * inside a sandboxed frame whenever some other subscribed field changed alone.
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
 * What the snapshot holds now counts as already sent, so "changed" means changed
 * since the subscription rather than since the process started. Without this the
 * first push fires whatever moved.
 */
const remember = (subscription: Subscription) => void changedSince(subscription, editorContext.value);

/**
 * Every frame of the extension hears it, because a panel and the entry frame are
 * two contexts of one extension and either may hold the handler. A frame that
 * asked for nothing drops the message on its own side, where its listener list
 * is the thing that knows.
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
 * A second call adds its fields rather than replacing them. Every handler in a
 * frame listens on the same `context` event, so a replacement would leave the
 * first handler silent with nothing to explain it.
 */
const subscribe = (params: unknown, extension: InstalledExtension) => {
	const wanted = readFields(params);
	const known = subscriptions.get(extension.name);
	if (known) {
		wanted.forEach((field) => known.fields.add(field));
		remember(known);
		return;
	}

	const subscription: Subscription = {
		fields: new Set(wanted),
		sent: new Map(),
		push: useThrottleFn(() => send(extension.name), THROTTLE_MS, true),
	};
	remember(subscription);
	subscriptions.set(extension.name, subscription);
	bridge.registerTeardown(extension.name, () => forget(extension.name));

	// no first push: `context.get` is the startup path, so the watcher stays lazy
	stopWatching ??= watch(editorContext, () => subscriptions.forEach((entry) => entry.push()));
};

export const contextMethods: MethodTable = {
	"context.get": { needs: "context.read", run: () => editorContext.value },
	"context.subscribe": { needs: "context.read", run: subscribe },
};
