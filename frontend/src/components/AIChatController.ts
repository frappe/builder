import type Block from "@/block";
import { BatchTracker } from "@/components/ai/batches";
import { setCostCurrency } from "@/components/ai/format";
import builderVariables from "@/data/builderVariable";
import { type AIChatHandlers, attachAIChatListeners, detachAIChatListeners } from "@/components/ai/realtime";
import { ToolDispatcher } from "@/components/ai/toolDispatch";
import type { AIProvider, ChatMessage } from "@/components/ai/types";
import { buildLocalMessage } from "@/components/ai/yaml";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { confirm } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { createResource, toast } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";
import router from "@/router";
import { useRoute } from "vue-router";

// Re-exported for components that still import these from here.
export type { AffectedBlock, AffectedScript, AIModel, AIProvider, ChatMessage } from "@/components/ai/types";

/**
 * Orchestrates the Builder AI chat: holds UI state, sends each user turn to the
 * single `builder.ai.api.run` endpoint, and reacts to the `ai_chat_*` realtime
 * events. Block-tree mutation lives in ToolDispatcher; YAML parsing in ./ai/yaml.
 */
export class AIChatController {
	private readonly builderStore = useBuilderStore();
	private readonly canvasStore = useCanvasStore();
	private readonly pageStore = usePageStore();
	private readonly route = useRoute();
	private readonly dispatcher: ToolDispatcher;

	readonly prompt = ref("");
	readonly progressMessage = ref("");
	readonly isSubmitting = ref(false);
	readonly isCancelling = ref(false); // true between clicking stop and the backend's cancelled event
	readonly messageContainer = ref<HTMLElement | null>(null);

	readonly imageData = ref<string | null>(null);
	readonly imagePreviewUrl = ref<string | null>(null);
	readonly imageFileName = ref("");
	readonly isDragging = ref(false);

	readonly sessionId = ref("");
	readonly messages = ref<ChatMessage[]>([]);
	// This page's chat sessions (most recent first) — the panel's session switcher.
	readonly sessions = ref<Array<{ name: string; title: string | null }>>([]);
	readonly availableModels = ref<AIProvider[]>([]);
	readonly selectedModel = useLocalStorage("ai-selected-model", "");

	// spawn_parallel_agents fan-outs this session — the task-group card's state.
	readonly batchTracker = new BatchTracker();
	readonly batches = this.batchTracker.batches;
	readonly publishingBatch = ref(false);

	// Floating build indicator. originPage: a build driven from ANOTHER chat is
	// writing to THIS page (watch-live) — link back to that chat. targetPage: this
	// chat's agent is building a DIFFERENT page — link there to watch it live.
	readonly foreignBuild = ref<{ originPage: string | null; targetPage: string | null } | null>(null);
	private foreignBuildTimer: ReturnType<typeof setTimeout> | null = null;

	private noteForeignBuild(originPage?: string | null, targetPage?: string | null) {
		this.foreignBuild.value = { originPage: originPage || null, targetPage: targetPage || null };
		if (this.foreignBuildTimer) clearTimeout(this.foreignBuildTimer);
		// No completion event is guaranteed to reach us; fade the pill out once the
		// stream goes quiet.
		this.foreignBuildTimer = setTimeout(() => (this.foreignBuild.value = null), 8000);
	}

	/** While a build stream owns this page's canvas, the editor's autosave stands
	 * down — persisting the partial preview is how a mid-build refresh (or an
	 * off-target render) corrupts the draft. The server saves the real result. */
	private buildQuietTimer: ReturnType<typeof setTimeout> | null = null;

	private beginCanvasBuild() {
		this.builderStore.aiBuildingCanvas = true;
		if (this.buildQuietTimer) clearTimeout(this.buildQuietTimer);
		// If the run dies without a complete event, release the canvas and resync
		// the draft from the server so the user isn't left editing a dead preview.
		this.buildQuietTimer = setTimeout(() => this.endCanvasBuild(true), 45000);
	}

	private endCanvasBuild(resyncDraft = false) {
		if (this.buildQuietTimer) {
			clearTimeout(this.buildQuietTimer);
			this.buildQuietTimer = null;
		}
		if (!this.builderStore.aiBuildingCanvas) return;
		this.builderStore.aiBuildingCanvas = false;
		if (resyncDraft && this.pageId.value && this.pageId.value !== "new") {
			this.pageStore.setPage(this.pageId.value, false);
		}
	}

	/** Accept one page_yaml chunk for the canvas. Drops chunks meant for another
	 * page (pill instead of paint), dedupes replayed chunks by stream offset, and
	 * refetches the server buffer when a gap shows we missed some. */
	private acceptPageYamlChunk(data: {
		chunk?: string;
		page_id?: string;
		offset?: number;
		origin_page?: string;
	}): void {
		if (data.page_id && data.page_id !== this.pageId.value) {
			this.noteForeignBuild(null, data.page_id);
			return;
		}
		if (typeof data.offset === "number") {
			const have = this.pageStreamContent.value.length;
			if (data.offset < have) return;
			if (data.offset > have) {
				this.syncActiveBuild();
				return;
			}
		}
		this.beginCanvasBuild();
		this.pageStreamContent.value += data.chunk!;
		this.scheduleStreamRender();
	}

	/** A mid-build page load: replay the in-flight generation stream from the
	 * server's buffer so the canvas shows the live build, not the stale draft. */
	private async syncActiveBuild() {
		const pid = this.pageId.value;
		if (!pid || pid === "new") return;
		const build: any = await createResource({ url: "builder.ai.api.get_active_build" })
			.submit({ page_id: pid })
			.catch(() => null);
		if (!build?.yaml || this.pageId.value !== pid) return;
		if (build.yaml.length <= this.pageStreamContent.value.length) return;
		this.beginCanvasBuild();
		this.pageStreamContent.value = build.yaml;
		if (build.origin_page && build.origin_page !== pid) {
			this.noteForeignBuild(build.origin_page);
		}
		this.scheduleStreamRender();
	}

	// Set by the panel's style-preset picker; folded into the prompt on submit.
	pendingStylePreset: string | null = null;
	// Compact display line for a card-composed reply (set by selectOption).
	private pendingDisplayText: string | null = null;

	private readonly pageStreamContent = ref(""); // accumulates kind="page_yaml" chunks
	private readonly summaryContent = ref(""); // accumulates summary chunks
	private readonly pendingAssistantId = ref<string | null>(null);
	private submittedForPageId: string | null = null;
	// Streaming re-render is throttled: re-parsing + rebuilding the whole block tree
	// on every chunk pegs the CPU. The final generate_page op re-applies the
	// authoritative document, so this preview can render at a coarse cadence.
	private static readonly STREAM_RENDER_MS = 200;
	private streamRenderTimer: ReturnType<typeof setTimeout> | null = null;
	private lastStreamRenderAt = 0;

	readonly pageId = computed(() => this.route.params.pageId as string);
	readonly isUnsavedPage = computed(() => !this.pageId.value || this.pageId.value === "new");
	readonly currentProviderModels = computed(
		() => this.availableModels.value.find((p) => p.provider === "openrouter")?.models || [],
	);
	readonly selectedBlocks = computed<Block[]>(
		() => (this.canvasStore.activeCanvas?.selectedBlocks || []) as Block[],
	);
	readonly modelLabel = computed(
		() =>
			this.currentProviderModels.value.find((m) => m.name === this.selectedModel.value)?.label ||
			"Select model",
	);
	readonly modelOptions = computed(() =>
		this.currentProviderModels.value.map((m) => ({
			label: m.label,
			onClick: () => (this.selectedModel.value = m.name),
		})),
	);
	readonly isVisionModel = computed(
		() => this.currentProviderModels.value.find((m) => m.name === this.selectedModel.value)?.vision ?? false,
	);
	readonly canSubmit = computed(
		() => !!this.prompt.value.trim() && !this.isSubmitting.value && !!this.selectedModel.value,
	);

	constructor() {
		this.dispatcher = new ToolDispatcher(this.pageStore, this.canvasStore, () => this.pageId.value);

		watch(
			this.currentProviderModels,
			(models) => {
				const isValid = models.some((m) => m.name === this.selectedModel.value);
				if (models.length && (!this.selectedModel.value || !isValid)) {
					this.selectedModel.value = models[0].name;
				}
			},
			{ immediate: true },
		);

		watch(this.pageId, async (newPageId, oldPageId) => {
			if (oldPageId) detachAIChatListeners(this.builderStore.realtime, oldPageId, this.handlers);
			if (!newPageId) return;
			attachAIChatListeners(this.builderStore.realtime, newPageId, this.handlers);
			this.resetTransientState();
			// Sessions are page-scoped: never carry one across a page switch.
			this.sessionId.value = "";
			this.sessions.value = [];
			if (newPageId === "new") {
				this.messages.value = [];
				return;
			}
			await this.loadSession();
			// A build may be mid-stream on this page (opened from another chat's link,
			// or a refresh mid-generation): replay the buffered stream as live preview.
			this.syncActiveBuild();
		});
	}

	private get handlers(): AIChatHandlers {
		return {
			onProgress: this.onProgress,
			onStream: this.onStream,
			onToolBatch: this.onToolBatch,
			onClarify: this.onClarify,
			onComplete: this.onComplete,
			onError: this.onError,
			onTaskGroup: this.onTaskGroup,
			onRefetch: this.onRefetch,
		};
	}

	resetTransientState() {
		this.clearStreamRenderTimer();
		this.endCanvasBuild();
		this.progressMessage.value = "";
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.pendingAssistantId.value = null;
		this.dispatcher.reset();
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
	}

	/** Throttle the streaming canvas preview: render at most every STREAM_RENDER_MS
	 * (leading + trailing) instead of re-parsing/rebuilding the whole tree per chunk. */
	private scheduleStreamRender() {
		const elapsed = Date.now() - this.lastStreamRenderAt;
		if (elapsed >= AIChatController.STREAM_RENDER_MS) {
			this.flushStreamRender();
		} else if (this.streamRenderTimer === null) {
			this.streamRenderTimer = setTimeout(
				() => this.flushStreamRender(),
				AIChatController.STREAM_RENDER_MS - elapsed,
			);
		}
	}

	private flushStreamRender() {
		this.clearStreamRenderTimer();
		this.lastStreamRenderAt = Date.now();
		try {
			this.dispatcher.applyPageYaml(this.pageStreamContent.value);
		} catch {}
	}

	private clearStreamRenderTimer() {
		if (this.streamRenderTimer !== null) {
			clearTimeout(this.streamRenderTimer);
			this.streamRenderTimer = null;
		}
	}

	private replacePendingAssistant(content: string, metadata: Record<string, any> = {}) {
		if (!this.pendingAssistantId.value) return;
		const index = this.messages.value.findIndex((m) => m.id === this.pendingAssistantId.value);
		if (index === -1) return;
		this.messages.value[index] = {
			...this.messages.value[index],
			content,
			metadata: { ...this.messages.value[index].metadata, ...metadata },
		};
	}

	private scrollToBottom() {
		nextTick(() => {
			if (this.messageContainer.value) {
				this.messageContainer.value.scrollTop = this.messageContainer.value.scrollHeight;
			}
		});
	}

	/** Load a chat session: the given one, else the current one, else the page's
	 * most recently used (the server creates the first). A page can hold several
	 * parallel sessions — see switchSession/newSession. */
	async loadSession(sessionId?: string) {
		if (!this.pageId.value || !this.builderStore.isAIEnabled || this.isUnsavedPage.value) return;
		const result = await createResource({
			url: "builder.ai.api.get_ai_session",
			makeParams: () => ({
				page_id: this.pageId.value,
				model: this.selectedModel.value,
				session_id: sessionId || this.sessionId.value || undefined,
			}),
		}).submit();
		const session = result as { session_id: string; messages: ChatMessage[] };
		this.sessionId.value = session.session_id;
		this.messages.value = (session.messages || []).map(
			(m) => ({ ...m, role: m.role === "user" ? "user" : "assistant" }) as ChatMessage,
		);
		// Rehydrate task-group cards: fetch each batch's durable state (polling
		// stops by itself once the batch settles).
		for (const m of this.messages.value) {
			const batchId = (m.metadata as any)?.batchId;
			if (batchId) this.batchTracker.track(batchId);
		}
		this.loadSessions();
	}

	/** Refresh the session-switcher list (fire-and-forget; the panel renders it). */
	loadSessions = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const rows = await createResource({ url: "builder.ai.api.list_page_ai_sessions" })
			.submit({ page_id: this.pageId.value })
			.catch(() => null);
		if (rows) this.sessions.value = rows as Array<{ name: string; title: string | null }>;
	};

	switchSession = async (sessionId: string) => {
		if (!sessionId || sessionId === this.sessionId.value) return;
		this.resetTransientState();
		await this.loadSession(sessionId);
		this.scrollToBottom();
	};

	newSession = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const result = await createResource({ url: "builder.ai.api.new_ai_session" }).submit({
			page_id: this.pageId.value,
			model: this.selectedModel.value,
		});
		this.resetTransientState();
		this.sessionId.value = (result as { session_id: string }).session_id;
		this.messages.value = [];
		this.loadSessions();
	};

	deleteSession = async () => {
		if (!this.sessionId.value) return;
		if (!(await confirm("Delete this chat? Its messages are removed; the page itself is untouched.")))
			return;
		await createResource({ url: "builder.ai.api.delete_ai_session" })
			.submit({ session_id: this.sessionId.value })
			.catch(() => null);
		this.resetTransientState();
		this.sessionId.value = "";
		await this.loadSession(); // falls back to the next most recent (or a fresh one)
	};

	clearImage = () => {
		this.imageData.value = null;
		this.imagePreviewUrl.value = null;
		this.imageFileName.value = "";
		this.isDragging.value = false;
	};

	attachImageFile = (file: File) => {
		if (!file.type.startsWith("image/")) return;
		if (file.size > 5 * 1024 * 1024) return;
		this.imageFileName.value = file.name || "pasted-image.png";
		const reader = new FileReader();
		reader.onload = (e) => {
			this.imageData.value = e.target?.result as string;
			this.imagePreviewUrl.value = this.imageData.value;
		};
		reader.readAsDataURL(file);
	};

	// --- realtime handlers ------------------------------------------------

	/** All events on this page's channel carry the session that produced them.
	 * With parallel sessions, chat-UI events from a session the user isn't
	 * viewing must not touch this view (canvas ops in onToolBatch still apply —
	 * the canvas is page-level, not session-level). */
	private isForeignSession(data: { session_id?: string }): boolean {
		return !!(data.session_id && this.sessionId.value && data.session_id !== this.sessionId.value);
	}

	onProgress = (data: { message?: string; session_id?: string }) => {
		if (this.isForeignSession(data)) return;
		this.isSubmitting.value = true;
		this.progressMessage.value = data.message || this.progressMessage.value;
		this.replacePendingAssistant(this.progressMessage.value || "Working...", { status: "running" });
		this.scrollToBottom();
	};

	onStream = (data: {
		chunk?: string;
		kind?: string;
		session_id?: string;
		origin_page?: string;
		page_id?: string;
		offset?: number;
	}) => {
		if (!data.chunk) return;
		if (this.isForeignSession(data)) {
			// A build driven from ANOTHER chat is streaming onto this page (watch-live).
			// The canvas is page-level: apply the preview, and surface the floating
			// "building live" indicator — but keep chat-text chunks out of this session.
			if (data.kind === "page_yaml") {
				if (!data.page_id || data.page_id === this.pageId.value) {
					this.noteForeignBuild(data.origin_page);
				}
				this.acceptPageYamlChunk(data);
			}
			return;
		}
		this.isSubmitting.value = true;
		if (data.kind === "page_yaml") {
			this.acceptPageYamlChunk(data);
		} else {
			this.summaryContent.value += data.chunk;
			this.replacePendingAssistant(this.summaryContent.value, { status: "running" });
			this.scrollToBottom();
		}
	};

	/** The agent fanned out parallel page builds (spawn_parallel_agents ends the
	 * turn). Track the batch so the panel's task-group card shows live progress;
	 * the reload on complete picks up the persisted message carrying batchId. */
	onTaskGroup = (data: {
		batch_id?: string;
		total?: number;
		tasks?: Array<Record<string, any>>;
		session_id?: string;
	}) => {
		if (!data.batch_id || this.isForeignSession(data)) return;
		this.batchTracker.track(data.batch_id, {
			total: data.total || data.tasks?.length || 0,
			tasks: (data.tasks || []).map((t: any) => ({ ...t })),
		});
	};

	/** A server tool changed state the canvas only loads at editor start. Refetch
	 * exactly what changed so mid-turn results render without a manual refresh:
	 * theme variables (var(--id) styles), the evaluated page data (repeater
	 * previews), or the page doc (route/meta). NOT session-scoped — this state is
	 * page/site-level, so any chat's turn should refresh it. */
	onRefetch = async (data: { resources?: string[] }) => {
		const resources = data.resources || [];
		if (resources.includes("variables")) {
			builderVariables.reload();
		}
		if (resources.includes("page_data") || resources.includes("page")) {
			const page = await this.pageStore.fetchActivePage(this.pageId.value).catch(() => null);
			if (page) {
				this.pageStore.activePage = page;
				if (resources.includes("page_data")) await this.pageStore.setPageData(page);
			}
		}
	};

	cancelBatch = (batchId: string) => this.batchTracker.cancel(batchId);

	publishBatch = async (batchId: string) => {
		this.publishingBatch.value = true;
		try {
			const res: any = await this.batchTracker.publish(batchId);
			toast.success(res?.message || "Published");
		} catch (e: any) {
			toast.error(e?.messages?.[0] || "Could not publish");
		} finally {
			this.publishingBatch.value = false;
		}
	};

	onToolBatch = (data: {
		page_id?: string;
		session_id?: string;
		origin_page?: string;
		operations?: Array<{ tool_name: string; args: Record<string, any> }>;
	}) => {
		// Cancel any pending throttled stream render so it can't fire AFTER and clobber
		// the authoritative apply below with stale partial YAML.
		this.clearStreamRenderTimer();
		if (!data.operations?.length) return;
		if (this.isForeignSession(data)) this.noteForeignBuild(data.origin_page);
		// The agent may focus another page mid-turn (open_page/create_page): its ops
		// are applied server-side; the canvas only mirrors ops for the page it shows.
		if (data.page_id && data.page_id !== this.pageId.value) {
			if (!this.isForeignSession(data)) this.noteForeignBuild(null, data.page_id);
			return;
		}
		for (const op of data.operations) {
			this.dispatcher.trackAffectedItem(op.tool_name, op.args); // track before apply (remove_block)
			try {
				this.dispatcher.applyToolOperation(op.tool_name, op.args);
			} catch (e) {
				console.warn(`[AI agent] tool "${op.tool_name}" failed:`, e);
			}
		}
		// Don't overwrite the bubble with a static "Applying N changes…" — the loop emits
		// a per-round progress note (the model's words, or a "Updated N blocks" summary)
		// right after each batch, which is what the user actually sees update.
		this.scrollToBottom();
	};

	onComplete = async (data: { message?: string; session_id?: string }) => {
		if (this.isForeignSession(data)) {
			// The other chat's build on this page finished; the authoritative
			// tool_batch already replaced the streamed preview.
			this.foreignBuild.value = null;
			this.endCanvasBuild();
			return;
		}
		this.clearStreamRenderTimer();
		this.endCanvasBuild();
		if (this.submittedForPageId && this.submittedForPageId !== this.pageId.value) {
			this.submittedForPageId = null;
			return;
		}
		this.submittedForPageId = null;
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.progressMessage.value = data.message || "Done";

		let undoScripts: string[] = [];
		if (this.dispatcher.pendingScriptOps.value.length) {
			const names = await Promise.all(this.dispatcher.pendingScriptOps.value);
			undoScripts = names.filter((n): n is string => !!n);
			this.dispatcher.pendingScriptOps.value = [];
		}
		for (const name of undoScripts) {
			if (!this.dispatcher.pendingAffectedScripts.value.find((s) => s.script_name === name)) {
				this.dispatcher.pendingAffectedScripts.value.push({ script_name: name, changedProps: ["created"] });
			}
		}

		const meta: Record<string, any> = { status: "complete" };
		if (undoScripts.length) meta.undoScripts = undoScripts;
		if (this.dispatcher.pendingAffectedBlocks.value.length)
			meta.affectedBlocks = [...this.dispatcher.pendingAffectedBlocks.value];
		if (this.dispatcher.pendingAffectedScripts.value.length)
			meta.affectedScripts = [...this.dispatcher.pendingAffectedScripts.value];
		this.replacePendingAssistant(this.progressMessage.value, meta);
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.dispatcher.reset();

		const localMeta = { ...meta };
		if (
			this.sessionId.value &&
			(localMeta.affectedBlocks?.length || localMeta.affectedScripts?.length || localMeta.undoScripts?.length)
		) {
			createResource({ url: "builder.ai.api.update_session_message_metadata" })
				.submit({ session_id: this.sessionId.value, metadata: localMeta })
				.catch(() => null);
		}

		await this.loadSession();

		// Re-apply client-only metadata in case the server hasn't flushed it yet.
		if (
			localMeta.affectedBlocks?.length ||
			localMeta.affectedScripts?.length ||
			localMeta.undoScripts?.length
		) {
			let idx = this.messages.value.length - 1;
			while (idx >= 0 && this.messages.value[idx]?.role !== "assistant") idx--;
			if (idx >= 0) {
				this.messages.value[idx] = {
					...this.messages.value[idx],
					metadata: { ...this.messages.value[idx].metadata, ...localMeta },
				};
			}
		}

		this.scrollToBottom();
		window.setTimeout(() => {
			this.progressMessage.value = "";
			this.pendingAssistantId.value = null;
		}, 1200);
	};

	onError = async (data: { message?: string; session_id?: string }) => {
		if (this.isForeignSession(data)) return;
		this.clearStreamRenderTimer();
		this.endCanvasBuild(!!this.pageStreamContent.value);
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.progressMessage.value = "";
		this.replacePendingAssistant(data.message || "Request failed", { status: "error" });
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		await this.loadSession();
		this.pendingAssistantId.value = null;
	};

	/** The agent composed a UI card (present_ui) — one generic renderer (AIUISpec)
	 * draws it. Confirm-gated actions arrive as pending_action instead and keep
	 * their dedicated Apply/Skip card. */
	onClarify = async (data: {
		question?: string;
		ui?: Array<Record<string, any>>;
		pending_action?: { kind: string; payload: Record<string, any> };
		session_id?: string;
	}) => {
		if (this.isForeignSession(data)) return;
		this.clearStreamRenderTimer();
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.progressMessage.value = "";
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";

		if (data.pending_action) {
			this.replacePendingAssistant(data.question || "Confirm this change?", {
				status: "pending_action",
				kind: data.pending_action.kind,
				payload: data.pending_action.payload,
			});
		} else {
			this.replacePendingAssistant(data.question || "…", {
				status: "ui",
				text: data.question || "",
				ui: data.ui || [],
			});
		}
		this.pendingAssistantId.value = null;
		// Backend persists+commits clarify messages before emitting, so this is race-free.
		await this.loadSession();
		this.scrollToBottom();
	};

	// --- user actions -----------------------------------------------------

	/** Submit a reply composed by an agent UI card (option tap, action button,
	 * collected form values) as the user's next ordinary message. `display` is
	 * the compact line the chat shows instead of the full relay — the model
	 * still receives the full reply. */
	selectOption = (option: string, display?: string) => {
		this.prompt.value = option;
		this.pendingDisplayText = display?.trim() || null;
		this.submitPrompt();
	};

	/** Apply or skip a sensitive action the agent proposed (create doctype, seed data,
	 * global settings, publish). The privileged write happens server-side in the endpoint;
	 * we reload the session so the message's status flips out of "pending_action". */
	confirmPendingAction = async (message: ChatMessage, decision: "apply" | "skip") => {
		try {
			const res = await createResource({
				url: "builder.ai.api.confirm_pending_settings",
				method: "POST",
			}).submit({ message_id: message.id, decision });
			await this.loadSession();
			if (decision === "apply") toast.success(res?.message || "Applied");
		} catch (e: any) {
			toast.error(e?.messages?.[0] || "Could not apply the change");
		}
	};


	/** Ask the backend to abort the in-flight turn at its next stream chunk.
	 * Anthropic/OpenRouter stop billing once the stream is closed. The backend's
	 * cancelled `complete` event lands only after the next chunk + a round trip,
	 * so we show "Cancelling" locally right away for instant feedback; that event
	 * (or onError/onClarify) clears isCancelling when the turn actually ends. */
	cancel = async () => {
		if (!this.sessionId.value || !this.isSubmitting.value || this.isCancelling.value) return;
		this.isCancelling.value = true;
		this.progressMessage.value = "Cancelling...";
		this.replacePendingAssistant("Cancelling...", { status: "running" });
		try {
			await createResource({ url: "builder.ai.api.cancel" }).submit({ session_id: this.sessionId.value });
		} catch {
			// Ignore — the user will see the event when it arrives.
		}
	};

	submitPrompt = async () => {
		if (!this.canSubmit.value || !this.pageId.value || this.isUnsavedPage.value) return;

		let userText = this.prompt.value.trim();
		this.prompt.value = "";
		if (this.pendingStylePreset) {
			userText += `\n\n(Preferred visual style: ${this.pendingStylePreset})`;
			this.pendingStylePreset = null;
		}
		this.submittedForPageId = this.pageId.value;
		if (!this.sessionId.value) await this.loadSession();

		const selectedBlockContext = this.selectedBlocks.value
			.filter((b) => b.blockId)
			.map((b) => ({ id: b.blockId, label: b.blockName || b.element }));
		const selectedIds = this.selectedBlocks.value.map((b) => b.blockId).filter(Boolean);
		const attachedImageData = this.imageData.value;
		const attachedImageUrl = this.imagePreviewUrl.value;
		this.clearImage();

		const displayText = this.pendingDisplayText;
		this.pendingDisplayText = null;

		const contextMeta: Record<string, any> = {};
		if (selectedBlockContext.length) contextMeta.selectedBlockContext = selectedBlockContext;
		if (attachedImageUrl) contextMeta.attachedImageUrl = attachedImageUrl;
		if (displayText) contextMeta.displayText = displayText;

		const userMessage = buildLocalMessage("user", userText, contextMeta);
		const assistantMessage = buildLocalMessage("assistant", "Thinking...", { status: "running" });
		this.messages.value.push(userMessage, assistantMessage);
		this.pendingAssistantId.value = assistantMessage.id;
		this.scrollToBottom();
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.dispatcher.reset();
		this.isSubmitting.value = true;

		// The server edits the page authoritatively from draft_blocks — flush any
		// unsaved canvas changes first so the turn (and its revert snapshot) starts
		// from exactly what the user sees.
		await this.pageStore.savePage();

		try {
			const result = await createResource({
				url: "builder.ai.api.run",
				makeParams: () => ({
					prompt: userText,
					page_id: this.pageId.value,
					model: this.selectedModel.value,
					session_id: this.sessionId.value,
					...(selectedIds.length ? { selected_block_ids: selectedIds } : {}),
					...(selectedBlockContext.length ? { selected_block_context: selectedBlockContext } : {}),
					...(attachedImageData ? { image_data: attachedImageData } : {}),
					...(displayText ? { display_text: displayText } : {}),
				}),
			}).submit();
			const response = result as { session_id?: string; status?: string; message?: string };
			if (response.session_id) this.sessionId.value = response.session_id;
		} catch (error) {
			await this.onError({ message: error instanceof Error ? error.message : "Request failed" });
		}
	};

	/** Revert an AI turn in ONE go: restore the page to the snapshot taken just before it
	 * — blocks, page data AND client scripts (created ones get unlinked, edited ones
	 * reverted) — and rewind the conversation, removing this message and everything after.
	 * The pre-turn snapshot is the single source of truth; there is no separate undo. */
	revertTurn = async (message: ChatMessage) => {
		const snapshot: string | undefined = message.metadata?.revertSnapshot;
		if (!snapshot || !this.sessionId.value) return;
		const confirmed = await confirm(
			"Revert this AI edit? The page (blocks and scripts) returns to how it was just before this turn, and this message and everything after it are removed from the chat. Your live page won't change until you publish.",
		);
		if (!confirmed) return;
		// 1. Rewind the conversation server-side (delete this turn + everything after).
		await createResource({ url: "builder.ai.api.revert_to_message" })
			.submit({ session_id: this.sessionId.value, message_id: message.id })
			.catch(() => null);
		// 2. Restore the page draft + scripts from the pre-turn snapshot. restore_snapshot
		// re-applies blocks, page data and the client-script set/content, then re-fetches
		// the page (which refreshes activePageScripts), so scripts revert in the same step.
		await this.pageStore.restoreSnapshot(snapshot);
		// 3. Reload the (now truncated) chat — restoreSnapshot doesn't touch the session.
		await this.loadSession();
		this.scrollToBottom();
	};

	selectBlockById = (blockId: string) => {
		const block = this.dispatcher.findBlockInTree(blockId);
		if (!block) return;
		this.canvasStore.selectBlock(block, null, true, true);
	};

	openScriptByName = (scriptName: string) => {
		this.builderStore.openClientScript = scriptName;
	};

	async mount() {
		if (this.pageId.value)
			attachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
		createResource({
			url: "builder.ai.api.get_ai_models",
			auto: true,
			onSuccess: (data: AIProvider[]) => {
				this.availableModels.value = data;
			},
		});
		// Costs display in the site's currency (converted from USD at a cached
		// daily rate); until this resolves they show as USD.
		createResource({ url: "builder.ai.api.get_ai_cost_currency", auto: true, onSuccess: setCostCurrency });
		await this.loadSession();
		await this.maybeRunInitialPrompt();
	}

	/** Auto-run a prompt handed off from the dashboard chat (an @page mention:
	 * "change the hero on @Home" navigates here with ?ai_prompt=…). Opens the chat
	 * tab, submits once a model is available, and strips the query so a refresh
	 * doesn't resubmit. */
	private async maybeRunInitialPrompt() {
		const initial = this.route.query.ai_prompt as string | undefined;
		if (!initial || this.isUnsavedPage.value) return;
		this.builderStore.leftPanelActiveTab = "Chat";
		const { ai_prompt, ...rest } = this.route.query;
		router.replace({ query: rest });
		// Wait briefly for the model list (mount fetches it async); bail if none.
		for (let i = 0; i < 40 && !this.selectedModel.value; i++) {
			await new Promise((r) => setTimeout(r, 100));
		}
		if (!this.selectedModel.value) return;
		this.prompt.value = initial;
		await nextTick();
		this.submitPrompt();
	}

	unmount() {
		if (this.pageId.value)
			detachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
		this.batchTracker.stopAll();
	}
}
