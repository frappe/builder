/** The unified `ai_chat_*` realtime event family. Each event name is suffixed
 * with the page id by the backend (see builder/ai/agent/loop.py). */

type Handler = (data: any) => void;

export interface AIChatHandlers {
	onProgress: Handler;
	onStream: Handler;
	onToolBatch: Handler;
	onClarify: Handler;
	onComplete: Handler;
	onError: Handler;
	/** Per-tool live activity ({tool, summary, status}) — drives the "what Bob is
	 * doing right now" status while a round runs its tool calls. */
	onToolActivity?: Handler;
	/** A spawn_parallel_agents fan-out started this turn (batch id + task list). */
	onTaskGroup?: Handler;
	/** A server tool changed state the canvas loads once at editor start
	 * (theme variables, page data, page doc) — refetch the named resources. */
	onRefetch?: Handler;
}

interface Realtime {
	on: (event: string, handler: Handler) => void;
	off: (event: string, handler: Handler) => void;
}

function listenerMap(h: AIChatHandlers): Record<string, Handler> {
	const map: Record<string, Handler> = {
		ai_chat_progress: h.onProgress,
		ai_chat_stream: h.onStream,
		ai_chat_tool_batch: h.onToolBatch,
		ai_chat_clarify: h.onClarify,
		ai_chat_complete: h.onComplete,
		ai_chat_error: h.onError,
	};
	if (h.onToolActivity) map.ai_chat_tool_activity = h.onToolActivity;
	if (h.onTaskGroup) map.ai_chat_task_group = h.onTaskGroup;
	if (h.onRefetch) map.ai_chat_refetch = h.onRefetch;
	return map;
}

const eventName = (base: string, pageId: string) => (pageId ? `${base}_${pageId}` : base);

export function attachAIChatListeners(realtime: Realtime, pageId: string, handlers: AIChatHandlers) {
	const map = listenerMap(handlers);
	Object.entries(map).forEach(([base, handler]) => realtime.on(eventName(base, pageId), handler));
}

export function detachAIChatListeners(realtime: Realtime, pageId: string, handlers: AIChatHandlers) {
	const map = listenerMap(handlers);
	Object.entries(map).forEach(([base, handler]) => realtime.off(eventName(base, pageId), handler));
}
