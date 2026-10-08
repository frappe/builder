/**
 * The action handlers of this frame. The host keeps only their names and calls back.
 * Only the entry frame keeps handlers, because it stays open the longest.
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

export const handleRequest = (method: string, params: unknown) => {
	const handler = methods.get(method);
	if (!handler) throw unknownMethod(method);
	return handler(params);
};
