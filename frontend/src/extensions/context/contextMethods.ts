/**
 * Methods that read the editor snapshot, or push it when it changes.
 * A push does not use the message budget. The throttle limits it.
 * One watcher serves the subscriptions of all extensions.
 */

import { useThrottleFn } from "@vueuse/core";
import { watch } from "vue";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import { fields as asFields, oneOf, refuse } from "../bridge/params";
import type { EditorContext, InstalledExtension } from "frappe-builder-extension-sdk/types";
import { editorContext } from "./editorContext";

/** The fields that an extension can subscribe to. */
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

/** A drag on the canvas sends only a few messages. A user does not see the delay. */
const THROTTLE_MS = 100;

type Subscription = {
	fields: Set<ContextField>;
	/** The last sent value of each field, as JSON. */
	sent: Map<ContextField, string>;
	push: () => void;
};

const subscriptions = new Map<string, Subscription>();

/**
 * The first subscription starts the watcher, not the module load.
 * So tests can import this module without pinia.
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
 * Returns the subscribed fields if one of them changed. Else returns null.
 * The payload has all subscribed fields. So a handler can read each field.
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
 * Marks the current value of new fields as sent.
 * Do not use it for old fields. They can have a change that waits for the throttle.
 */
const remember = (subscription: Subscription, fields: ContextField[]) =>
	fields.forEach((field) => subscription.sent.set(field, JSON.stringify(editorContext.value[field])));

/** Sends to each frame of the extension. A frame with no listener ignores the message. */
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

/** A second call adds its fields. It does not replace the fields of the first call. */
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

	// No push at the start. The extension calls `context.get` for the first value.
	stopWatching ??= watch(editorContext, () => subscriptions.forEach((entry) => entry.push()));
};

export const contextMethods: MethodTable = {
	"context.get": { needs: null, run: () => editorContext.value },
	"context.subscribe": { needs: null, run: subscribe },
};
