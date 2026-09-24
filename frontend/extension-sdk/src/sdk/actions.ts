/**
 * The handlers this frame owns, and running the one the host asked for.
 *
 * A handler is a function, so it never crosses the port. The host holds only
 * the name, and calls back when a descriptor naming it is activated.
 *
 * Apart from `namespaces.ts` so that `connect.ts` can dispatch requests without
 * the two importing each other.
 *
 * Only the entry frame holds handlers. The host calls that frame because it
 * outlives visual slots, which can close while an action still appears on a
 * descriptor.
 */

import { unknownMethod } from "../transport/createPortChannel";

export type ActionHandler = (context: Record<string, unknown>) => unknown;

const handlers = new Map<string, ActionHandler>();

export const holdAction = (name: string, handler: ActionHandler) => handlers.set(name, handler);

export const releaseAction = (name: string) => handlers.delete(name);

export const runAction = (params: unknown) => {
	const { action, context } = (params ?? {}) as { action?: string; context?: Record<string, unknown> };
	const handler = handlers.get(String(action));
	if (!handler) throw new Error(`This extension registered no action named "${action}"`);
	return handler(context ?? {});
};

const methods = new Map<string, (params: unknown) => unknown>([["action.invoke", runAction]]);

export const dispatch = (method: string, params: unknown) => {
	const handler = methods.get(method);
	if (!handler) throw unknownMethod(method);
	return handler(params);
};
