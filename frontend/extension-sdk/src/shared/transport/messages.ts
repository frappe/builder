/**
 * Builds and checks the messages that cross a port. `../types` holds their shapes.
 *
 * Recognizing a message and accepting its version are two steps, and the types
 * enforce the order. A message at an unknown version is still routable, so the
 * channel can answer it rather than drop it.
 */

import {
	PROTOCOL_VERSION,
	type AnyVersionMessage,
	type ChannelError,
	type EventMessage,
	type PortMessage,
	type RequestMessage,
	type ResponseMessage,
} from "../types";

export const request = (id: number, method: string, params?: unknown): RequestMessage => ({
	v: PROTOCOL_VERSION,
	type: "request",
	id,
	method,
	params,
});

export const respond = (id: number, result?: unknown): ResponseMessage => ({
	v: PROTOCOL_VERSION,
	type: "response",
	id,
	result,
});

export const fail = (id: number, error: ChannelError): ResponseMessage => ({
	v: PROTOCOL_VERSION,
	type: "response",
	id,
	error,
});

export const event = (name: string, payload?: unknown): EventMessage => ({
	v: PROTOCOL_VERSION,
	type: "event",
	event: name,
	payload,
});

/** The only refusal the transport itself raises. Every other error comes from a method. */
export const unsupportedVersionError = (version: number): ChannelError => ({
	message: `This Builder speaks protocol version ${PROTOCOL_VERSION}, not ${version}.`,
	code: "unsupported_version",
});

export const unsupportedVersion = (id: number, version: number): ResponseMessage =>
	fail(id, unsupportedVersionError(version));

const isRecord = (value: unknown): value is Record<string, unknown> =>
	typeof value === "object" && value !== null;

/**
 * True for anything shaped like a port message, at any version.
 *
 * It checks only the fields that route a message. `params`, `result` and
 * `payload` belong to the method, and the host validates those per method.
 */
export const isPortMessage = (value: unknown): value is AnyVersionMessage => {
	if (!isRecord(value) || typeof value.v !== "number") return false;
	if (value.type === "request") return typeof value.id === "number" && typeof value.method === "string";
	if (value.type === "response") return typeof value.id === "number";
	if (value.type === "event") return typeof value.event === "string";
	return false;
};

export const isCurrentVersion = (message: AnyVersionMessage): message is PortMessage =>
	message.v === PROTOCOL_VERSION;
