/**
 * Reading what a frame sent.
 *
 * Every parameter arrives from another realm as unknown, and the host validates
 * all of them. A refusal carries a code, so the SDK can branch on it.
 */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";

export const refuse = (message: string, code: string) => new ChannelCallError({ message, code });

export const text = (value: unknown, field: string) => {
	if (typeof value !== "string" || !value.trim()) {
		throw refuse(`"${field}" must be a non-empty string.`, "invalid_params");
	}
	return value;
};

export const optionalText = (value: unknown, field: string) =>
	value === undefined ? undefined : text(value, field);

/** Keeps the current value when the patch says nothing about this field. */
export const flag = (value: unknown, current: boolean) => (typeof value === "boolean" ? value : current);

export const oneOf = <T extends string>(value: unknown, allowed: readonly T[], field: string): T => {
	if (!allowed.includes(value as T)) {
		throw refuse(`"${field}" must be one of: ${allowed.join(", ")}.`, "invalid_params");
	}
	return value as T;
};

export const wholeNumber = (value: unknown, field: string) => {
	if (!Number.isInteger(value) || (value as number) < 0) {
		throw refuse(`"${field}" must be a whole number.`, "invalid_params");
	}
	return value as number;
};

export const optionalWholeNumber = (value: unknown, field: string) =>
	value === undefined ? undefined : wholeNumber(value, field);

export const fields = (params: unknown) => (params ?? {}) as Record<string, unknown>;
