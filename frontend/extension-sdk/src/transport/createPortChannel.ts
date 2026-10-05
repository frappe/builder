/**
 * One `MessagePort` per extension frame, three verbs: `call`, `listen`, `emit`.
 * Builder groups the channels from an extension's frames by extension.
 *
 * The host and the SDK both use this. Neither side is a client, so nothing here
 * knows which end of a channel it runs on, or what methods exist.
 */

import type { AnyVersionMessage, ChannelError, EventMessage, PortMessage, RequestMessage } from "../types";
import {
	event as eventMessage,
	fail,
	isCurrentVersion,
	isPortMessage,
	request,
	respond,
	unsupportedVersion,
	unsupportedVersionError,
} from "./messages";

export type EventHandler = (payload: unknown) => void;

/** Resolves every request this end of the channel accepts. */
export type Dispatcher = (method: string, params: unknown) => unknown;

/** A refusal from the far side, or from the transport itself. */
export class ChannelCallError extends Error {
	code?: string;

	constructor(error: ChannelError) {
		super(error.message);
		this.name = "ChannelCallError";
		this.code = error.code;
	}
}

/** The refusal for a method nothing claims. A dispatcher raises it too, so it has one spelling. */
export const unknownMethod = (method: string) =>
	new ChannelCallError({ message: `Unknown method "${method}".`, code: "unknown_method" });

const CHANNEL_CLOSED: ChannelError = {
	message: "The extension channel is closed.",
	code: "channel_closed",
};

const toChannelError = (error: unknown): ChannelError => {
	if (error instanceof ChannelCallError) return { message: error.message, code: error.code };
	return { message: error instanceof Error ? error.message : String(error) };
};

export function createPortChannel(port: MessagePort, dispatcher?: Dispatcher) {
	const pending = new Map<number, { resolve: (value: unknown) => void; reject: (error: Error) => void }>();
	const listeners = new Map<string, Set<EventHandler>>();
	let nextId = 1;
	let closed = false;

	const post = (message: PortMessage) => {
		if (!closed) port.postMessage(message);
	};

	const run = (method: string, params: unknown) => {
		if (dispatcher) return dispatcher(method, params);
		throw unknownMethod(method);
	};

	const answer = async (message: RequestMessage) => {
		try {
			post(respond(message.id, await run(message.method, message.params)));
		} catch (error) {
			post(fail(message.id, toChannelError(error)));
		}
	};

	const settle = (id: number, result: unknown, error?: ChannelError) => {
		const call = pending.get(id);
		if (!call) return console.warn(`Extension channel received a response for unknown call ${id}`);
		pending.delete(id);
		if (error) call.reject(new ChannelCallError(error));
		else call.resolve(result);
	};

	const notify = (message: EventMessage) => {
		listeners.get(message.event)?.forEach((handler) => handler(message.payload));
	};

	// a request and a response both carry an id, so both can be answered. An event
	// cannot, so a version it does not speak leaves it nowhere to report
	const refuseVersion = (message: AnyVersionMessage) => {
		if (message.type === "request") return post(unsupportedVersion(message.id, message.v));
		if (message.type === "response") return settle(message.id, undefined, unsupportedVersionError(message.v));
		console.warn(`Extension channel dropped an event at protocol version ${message.v}`);
	};

	const receive = (data: unknown) => {
		if (!isPortMessage(data)) return;
		if (!isCurrentVersion(data)) return refuseVersion(data);
		if (data.type === "request") return void answer(data);
		if (data.type === "response") return settle(data.id, data.result, data.error);
		notify(data);
	};

	const call = <T = unknown>(method: string, params?: unknown) =>
		new Promise<T>((resolve, reject) => {
			if (closed) return reject(new ChannelCallError(CHANNEL_CLOSED));
			const id = nextId++;
			pending.set(id, { resolve: resolve as (value: unknown) => void, reject });
			post(request(id, method, params));
		});

	const listen = (name: string, handler: EventHandler) => {
		const forEvent = listeners.get(name) ?? new Set<EventHandler>();
		listeners.set(name, forEvent);
		forEvent.add(handler);
		return () => forEvent.delete(handler);
	};

	const emit = (name: string, payload?: unknown) => post(eventMessage(name, payload));

	/** Nothing outlives the port: every pending call rejects, and no goodbye is sent. */
	const close = () => {
		if (closed) return;
		closed = true;
		pending.forEach((call) => call.reject(new ChannelCallError(CHANNEL_CLOSED)));
		pending.clear();
		listeners.clear();
		port.close();
	};

	// assigning onmessage starts the port
	port.onmessage = (message: MessageEvent) => receive(message.data);

	return { call, listen, emit, close };
}

export type PortChannel = ReturnType<typeof createPortChannel>;
