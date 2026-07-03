import useBuilderStore from "@/stores/builderStore";
import { confirm } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { createResource, toast } from "frappe-ui";
import { computed, nextTick, ref } from "vue";

/**
 * The page-less dashboard AI chat. One general agent turn per send, streamed over the
 * session-scoped `ai_chat_*_<sessionId>` realtime events. Deliberately simple and
 * canvas-free (unlike AIChatController): the agent works through server tools +
 * parallel sub-agents, so we render its narration, task-group progress, and
 * clarify/confirm cards inline — no hardcoded pipeline.
 */

export interface ActivityEntry {
	id: number;
	tool: string;
	summary: string;
	status: string; // running | done
	page?: string; // working-page id → "Open" link on the line
}

export interface AgentMessage {
	id: string;
	role: "user" | "assistant";
	text: string;
	status: string; // running | complete | error | clarification | plan_summary | pending_action
	progress?: string;
	activity?: ActivityEntry[]; // live tool feed ("Read page: Home", …)
	attachedImage?: string; // image the user sent with this prompt
	revertSnapshot?: string; // pre-turn snapshot → the turn is revertable
	options?: string[];
	previews?: Array<{ colors: string[] }> | null;
	plan?: { headline: string; sections: string[]; palette: string };
	confirm?: { messageId: string; kind: string; payload: Record<string, any> };
	batchId?: string; // a spawn_parallel_agents fan-out introduced in this turn
}

export interface BatchState {
	batchId: string;
	status: string;
	projectFolder: string | null;
	total: number;
	completed: number;
	failed: number;
	tasks: Array<{
		row: string;
		title: string;
		page: string | null;
		status: string;
		error?: string;
		preview?: string | null;
	}>;
}

const EVENTS = [
	"progress",
	"stream",
	"tool_batch",
	"tool_activity",
	"clarify",
	"complete",
	"error",
	"task_group",
] as const;

let uid = 0;
const nextId = () => `m${++uid}`;

// Lazy: the Pinia store must not be resolved at module-import time (pinia may not be
// active yet). Called from within component lifecycle, where the store is ready.
const realtime = () => useBuilderStore().realtime;

const sessionId = ref("");
const messages = ref<AgentMessage[]>([]);
const sessions = ref<any[]>([]);
const batches = ref<Record<string, BatchState>>({});
const prompt = ref("");
const sending = ref(false);
const cancelling = ref(false);
const models = ref<Array<{ name: string; label: string; vision?: boolean }>>([]);
const selectedModel = useLocalStorage("ai-selected-model", "");
const messageContainer = ref<HTMLElement | null>(null);
// Image attached to the next prompt (data URL) — vision models only.
const imageData = ref<string | null>(null);

let boundSuffix = "";
const pollTimers: Record<string, ReturnType<typeof setInterval>> = {};

const canSubmit = computed(() => !!prompt.value.trim() && !sending.value && !!selectedModel.value);
const isVisionModel = computed(() => models.value.find((m) => m.name === selectedModel.value)?.vision ?? false);

function pending(): AgentMessage | null {
	for (let i = messages.value.length - 1; i >= 0; i--) {
		if (messages.value[i].role === "assistant") return messages.value[i];
	}
	return null;
}

/** The assistant bubble for the turn an event belongs to. Turns can start WITHOUT a
 * send from this client — a parallel build finishing resumes the agent in the
 * background — so when we're idle, open a fresh running bubble instead of mutating
 * the last settled message. */
function ensureTurnBubble(): AgentMessage | null {
	if (!sending.value) {
		messages.value.push({ id: nextId(), role: "assistant", text: "", status: "running" });
		sending.value = true;
	}
	return pending();
}

function scrollToBottom() {
	nextTick(() => {
		const el = messageContainer.value;
		if (el) el.scrollTop = el.scrollHeight;
	});
}

// --- realtime ---------------------------------------------------------

const handlers: Record<string, (data: any) => void> = {
	progress: (d) => {
		const m = ensureTurnBubble();
		if (!m) return;
		m.status = "running";
		if (d.message) m.progress = d.message;
		scrollToBottom();
	},
	stream: (d) => {
		if (!d.chunk || d.kind === "page_yaml") return;
		const m = ensureTurnBubble();
		if (!m) return;
		m.status = "running";
		m.text += d.chunk;
		scrollToBottom();
	},
	tool_batch: () => {}, // headless: no client ops to apply
	// One entry per server-tool call; the same id arrives twice (running → done) —
	// upsert by id.
	tool_activity: (d) => {
		const m = ensureTurnBubble();
		if (!m || d.id === undefined) return;
		m.status = "running";
		if (!m.activity) m.activity = [];
		const entry = { id: d.id, tool: d.tool, summary: d.summary, status: d.status, page: d.page };
		const i = m.activity.findIndex((a) => a.id === d.id);
		if (i === -1) m.activity.push(entry);
		else m.activity[i] = entry;
		scrollToBottom();
	},
	task_group: (d) => {
		const m = ensureTurnBubble();
		if (!m || !d.batch_id) return;
		m.batchId = d.batch_id;
		batches.value[d.batch_id] = {
			batchId: d.batch_id,
			status: "running",
			projectFolder: null,
			total: d.total || (d.tasks?.length ?? 0),
			completed: 0,
			failed: 0,
			tasks: (d.tasks || []).map((t: any) => ({ ...t })),
		};
		pollBatch(d.batch_id);
		scrollToBottom();
	},
	clarify: (d) => {
		const m = ensureTurnBubble();
		if (!m) return;
		m.progress = "";
		if (d.plan_summary) {
			m.status = "plan_summary";
			m.text = d.headline || "Here's my plan";
			m.plan = { headline: d.headline || "", sections: d.sections || [], palette: d.palette || "" };
		} else if (d.pending_action) {
			m.status = "pending_action";
			m.text = d.question || "Confirm this change?";
			m.confirm = { messageId: d.message_id || "", kind: d.pending_action.kind, payload: d.pending_action.payload };
		} else {
			m.status = "clarification";
			m.text = d.question || "Could you clarify?";
			m.options = d.options || [];
			m.previews = d.previews ?? null;
		}
		sending.value = false;
		cancelling.value = false;
		scrollToBottom();
	},
	complete: (d) => {
		const m = pending();
		if (m) {
			m.status = "complete";
			m.progress = "";
			if (!m.text) m.text = d.message || "Done";
		}
		sending.value = false;
		cancelling.value = false;
		loadSessions();
		syncLastAssistant(); // pick up the server message id + revertSnapshot
		scrollToBottom();
	},
	error: (d) => {
		const m = pending();
		if (m) {
			// A "warning" is a soft miss (e.g. the model read things but wrote no
			// reply) — informational, not a failure.
			m.status = d.warning ? "warning" : "error";
			m.progress = "";
			m.text = d.message || "Something went wrong.";
		}
		sending.value = false;
		cancelling.value = false;
		scrollToBottom();
	},
};

function subscribe(suffix: string) {
	unsubscribe();
	const rt = realtime();
	if (!suffix || !rt) return;
	boundSuffix = suffix;
	for (const e of EVENTS) rt.on(`ai_chat_${e}_${suffix}`, handlers[e]);
}

function unsubscribe() {
	const rt = realtime();
	if (boundSuffix && rt) {
		for (const e of EVENTS) rt.off(`ai_chat_${e}_${boundSuffix}`, handlers[e]);
	}
	boundSuffix = "";
}

// --- batch polling (durable source of truth for the task-group card) --

function pollBatch(batchId: string) {
	if (pollTimers[batchId]) return;
	const tick = async () => {
		try {
			const res: any = await createResource({ url: "builder.ai.api.get_ai_batch_status" }).submit({ batch_id: batchId });
			batches.value[batchId] = {
				batchId,
				status: res.status,
				projectFolder: res.project_folder || null,
				total: res.total_tasks,
				completed: res.completed_tasks,
				failed: res.failed_tasks,
				tasks: res.tasks || [],
			};
			if (["done", "failed", "cancelled"].includes(res.status)) {
				clearInterval(pollTimers[batchId]);
				delete pollTimers[batchId];
			}
		} catch {
			/* transient */
		}
	};
	tick();
	pollTimers[batchId] = setInterval(tick, 2500);
}

// --- loading ----------------------------------------------------------

async function loadModels() {
	try {
		const data: any = await createResource({ url: "builder.ai.api.get_ai_models" }).fetch();
		const provider = (data || []).find((p: any) => p.provider === "openrouter") || (data || [])[0];
		models.value = (provider?.models || []).map((m: any) => ({
			name: m.name,
			label: m.label,
			vision: m.vision,
		}));
		if (models.value.length && !models.value.some((m) => m.name === selectedModel.value)) {
			selectedModel.value = models.value[0].name;
		}
	} catch {
		/* ignore */
	}
}

async function loadSessions() {
	try {
		sessions.value = await createResource({ url: "builder.ai.api.list_ai_sessions" }).fetch();
	} catch {
		/* ignore */
	}
}

function hydrate(rows: any[]): AgentMessage[] {
	return (rows || []).map((r) => {
		const meta = r.metadata || {};
		const status = meta.status || "complete";
		const m: AgentMessage = { id: r.id || nextId(), role: r.role === "user" ? "user" : "assistant", text: r.content || "", status };
		if (Array.isArray(meta.activity) && meta.activity.length) {
			m.activity = meta.activity;
		}
		if (meta.attachedImageUrl) m.attachedImage = meta.attachedImageUrl;
		if (meta.revertSnapshot) m.revertSnapshot = meta.revertSnapshot;
		if (meta.batchId) m.batchId = meta.batchId;
		if (status === "clarification") {
			m.options = meta.options || [];
			m.previews = meta.previews ?? null;
		} else if (status === "plan_summary") {
			m.plan = { headline: meta.headline || r.content || "", sections: meta.sections || [], palette: meta.palette || "" };
		} else if (status === "pending_action") {
			m.confirm = { messageId: r.id, kind: meta.kind, payload: meta.payload || {} };
		}
		return m;
	});
}

async function open(routeSessionId?: string) {
	stopPolling();
	const url = routeSessionId ? "builder.ai.api.get_ai_session_messages" : "builder.ai.api.get_general_session";
	const params = routeSessionId ? { session_id: routeSessionId } : { model: selectedModel.value };
	const res: any = await createResource({ url }).submit(params);
	sessionId.value = res.session_id || "";
	messages.value = hydrate(res.messages);
	if (res.selected_model && !selectedModel.value) selectedModel.value = res.selected_model;
	subscribe(sessionId.value);
	// Rehydrate task-group cards: fetch each batch's durable state (pollBatch stops
	// itself once the batch is settled, so old batches cost one fetch).
	for (const m of messages.value) {
		if (m.batchId) pollBatch(m.batchId);
	}
	scrollToBottom();
}

// After a turn settles, adopt the persisted assistant message's identity — the
// server id (needed for revert), its revert snapshot, and the durable activity.
async function syncLastAssistant() {
	if (!sessionId.value) return;
	try {
		const res: any = await createResource({ url: "builder.ai.api.get_ai_session_messages" }).submit({
			session_id: sessionId.value,
		});
		const rows = (res.messages || []).filter((r: any) => r.role !== "user");
		const row = rows[rows.length - 1];
		const m = pending();
		if (!row || !m) return;
		m.id = row.id;
		const meta = row.metadata || {};
		if (meta.revertSnapshot) m.revertSnapshot = meta.revertSnapshot;
		if (Array.isArray(meta.activity) && meta.activity.length) m.activity = meta.activity;
	} catch {
		/* cosmetic — revert just won't show until reload */
	}
}

// --- actions ----------------------------------------------------------

function attachImageFile(file: File) {
	if (!file.type.startsWith("image/")) return;
	const reader = new FileReader();
	reader.onload = (e) => {
		imageData.value = (e.target?.result as string) || null;
	};
	reader.readAsDataURL(file);
}

function clearImage() {
	imageData.value = null;
}

async function send(mentionedPages: Array<{ name: string; title: string; route: string }> = []) {
	const text = prompt.value.trim();
	if (!text || sending.value || !selectedModel.value) return;
	prompt.value = "";
	const attached = imageData.value;
	imageData.value = null;
	messages.value.push({
		id: nextId(),
		role: "user",
		text,
		status: "complete",
		...(attached ? { attachedImage: attached } : {}),
	});
	messages.value.push({ id: nextId(), role: "assistant", text: "", status: "running", progress: "Thinking…" });
	sending.value = true;
	scrollToBottom();
	try {
		const res: any = await createResource({ url: "builder.ai.api.run", method: "POST" }).submit({
			prompt: text,
			model: selectedModel.value,
			session_id: sessionId.value || undefined,
			...(attached ? { image_data: attached } : {}),
			...(mentionedPages.length ? { mentioned_pages: mentionedPages } : {}),
		});
		if (res.session_id && !sessionId.value) {
			sessionId.value = res.session_id;
			subscribe(sessionId.value);
		}
	} catch (e: any) {
		handlers.error({ message: e?.messages?.[0] || "Request failed" });
	}
}

function selectOption(option: string) {
	prompt.value = option;
	send();
}

function approvePlan() {
	prompt.value = "Yes, that looks good — go ahead and build it.";
	send();
}

async function confirmAction(m: AgentMessage, decision: "apply" | "skip") {
	if (!m.confirm?.messageId) return;
	try {
		const res: any = await createResource({ url: "builder.ai.api.confirm_pending_settings", method: "POST" }).submit({
			message_id: m.confirm.messageId,
			decision,
		});
		m.status = decision === "apply" ? "action_applied" : "action_skipped";
		m.confirm = undefined;
		// The outcome is a real conversation message (the backend persisted the same
		// text), not just a toast — so what happened stays visible in the thread.
		messages.value.push({
			id: nextId(),
			role: "assistant",
			text: decision === "apply" ? res?.message || "Applied." : "Skipped — nothing was changed.",
			status: "complete",
		});
		// The decision resumes the agent's bigger task — surface the continuation.
		if (res?.resumed) {
			messages.value.push({
				id: nextId(),
				role: "assistant",
				text: "",
				status: "running",
				progress: "Continuing…",
			});
			sending.value = true;
		}
		scrollToBottom();
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not apply the change");
	}
}

/** Revert an AI turn in ONE go, mirroring the editor chat: the page returns to its
 * pre-turn snapshot (server-side restore into the draft) and the conversation is
 * rewound — this message and everything after it are removed. */
async function revertTurn(m: AgentMessage) {
	if (!m.revertSnapshot || !sessionId.value || sending.value) return;
	const confirmed = await confirm(
		"Revert this AI edit? The page returns to how it was just before this turn, and this message and everything after it are removed from the chat. Your live page won't change until you publish.",
	);
	if (!confirmed) return;
	try {
		const res: any = await createResource({ url: "builder.ai.api.revert_ai_turn", method: "POST" }).submit(
			{ session_id: sessionId.value, message_id: m.id },
		);
		messages.value = hydrate(res.messages);
		toast.success("Reverted");
		scrollToBottom();
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not revert");
	}
}

async function renameSession(id: string, title: string) {
	try {
		await createResource({ url: "builder.ai.api.rename_ai_session", method: "POST" }).submit({
			session_id: id,
			title,
		});
		await loadSessions();
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not rename");
	}
}

async function deleteSession(id: string): Promise<boolean> {
	const confirmed = await confirm("Delete this chat? Its messages are removed permanently.");
	if (!confirmed) return false;
	try {
		await createResource({ url: "builder.ai.api.delete_ai_session", method: "POST" }).submit({
			session_id: id,
		});
		await loadSessions();
		return true;
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not delete");
		return false;
	}
}

async function cancel() {
	if (!sessionId.value || !sending.value || cancelling.value) return;
	cancelling.value = true;
	const m = pending();
	if (m) m.progress = "Cancelling…";
	try {
		await createResource({ url: "builder.ai.api.cancel" }).submit({ session_id: sessionId.value });
	} catch {
		/* the cancelled event will arrive */
	}
}

async function cancelBatch(batchId: string) {
	try {
		await createResource({ url: "builder.ai.api.cancel_ai_batch", method: "POST" }).submit({
			batch_id: batchId,
		});
		toast.success("Stopping…");
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not stop the build");
	}
}

async function publishBatch(batchId: string) {
	try {
		const res: any = await createResource({ url: "builder.ai.api.publish_site_batch", method: "POST" }).submit({ batch_id: batchId });
		toast.success(res?.message || "Published");
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Publish failed");
	}
}

function stopPolling() {
	for (const id of Object.keys(pollTimers)) {
		clearInterval(pollTimers[id]);
		delete pollTimers[id];
	}
}

function teardown() {
	unsubscribe();
	stopPolling();
}

export function useAgentChat() {
	return {
		sessionId,
		messages,
		sessions,
		batches,
		prompt,
		sending,
		cancelling,
		models,
		selectedModel,
		messageContainer,
		canSubmit,
		isVisionModel,
		imageData,
		attachImageFile,
		clearImage,
		loadModels,
		loadSessions,
		open,
		send,
		selectOption,
		approvePlan,
		confirmAction,
		revertTurn,
		renameSession,
		deleteSession,
		cancel,
		cancelBatch,
		publishBatch,
		teardown,
	};
}
