/**
 * The handlers that this frame keeps, and how to run one when the host asks.
 *
 * A handler is a function, so it cannot go through the port. The host keeps
 * only the name. When a user activates a descriptor with that name, the host
 * calls back.
 *
 * This code is separate from `namespaces.ts`. So `connect.ts` can dispatch
 * requests, and the two files do not import each other.
 *
 * Only the entry frame keeps handlers. The host calls that frame because it
 * lives longer than visual slots. A slot can close while a descriptor still
 * shows its action.
 */

import { unknownMethod } from "../shared/transport/createPortChannel";

export type ActionHandler = (context: Record<string, unknown>) => unknown;

const handlers = new Map<string, ActionHandler>();

export const setHandler = (name: string, handler: ActionHandler) => handlers.set(name, handler);

export const deleteHandler = (name: string) => handlers.delete(name);

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
