/**
 * A channel on one `MessagePort` for each frame, with `call`, `listen` and `emit`.
 * The host and the SDK both use this file. It does not know its side or the methods.
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

/** Answers each request that this side accepts. */
export type RequestHandler = (method: string, params: unknown) => unknown;

/** An error from the other side, or from the transport. */
export class ChannelCallError extends Error {
	code?: string;

	constructor(error: ChannelError) {
		super(error.message);
		this.name = "ChannelCallError";
		this.code = error.code;
	}
}

/** The error for an unknown method. A request handler also uses it. */
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

export function createPortChannel(port: MessagePort, requestHandler?: RequestHandler) {
	const pending = new Map<number, { resolve: (value: unknown) => void; reject: (error: Error) => void }>();
	const listeners = new Map<string, Set<EventHandler>>();
	let nextId = 1;
	let closed = false;

	const post = (message: PortMessage) => {
		if (!closed) port.postMessage(message);
	};

	const run = (method: string, params: unknown) => {
		if (requestHandler) return requestHandler(method, params);
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

	// A request and a response have an id. So the channel can answer an unknown version.
	// An event has no id. So the channel cannot answer it.
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
			// Post first. It throws if it cannot copy the params.
			post(request(id, method, params));
			pending.set(id, { resolve: resolve as (value: unknown) => void, reject });
		});

	const listen = (name: string, handler: EventHandler) => {
		const forEvent = listeners.get(name) ?? new Set<EventHandler>();
		listeners.set(name, forEvent);
		forEvent.add(handler);
		return () => forEvent.delete(handler);
	};

	const emit = (name: string, payload?: unknown) => post(eventMessage(name, payload));

	/** Closes the channel and the port. Each pending call fails. */
	const close = () => {
		if (closed) return;
		closed = true;
		pending.forEach((call) => call.reject(new ChannelCallError(CHANNEL_CLOSED)));
		pending.clear();
		listeners.clear();
		port.close();
	};

	// Setting onmessage starts the port.
	port.onmessage = (message: MessageEvent) => receive(message.data);

	return { call, listen, emit, close };
}

export type PortChannel = ReturnType<typeof createPortChannel>;
