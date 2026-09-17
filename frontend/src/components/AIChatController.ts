import type Block from "@/block";
import builderTokens from "@/data/builderToken";
import { type AIChatHandlers, attachAIChatListeners, detachAIChatListeners } from "@/components/ai/realtime";
import { ToolDispatcher } from "@/components/ai/toolDispatch";
import type { AIProvider, AITurnStep, ChatMessage } from "@/components/ai/types";
import { buildLocalMessage } from "@/components/ai/yaml";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { confirm } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { createResource, toast } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";

// Re-exported for components that still import these from here.
export type {
	AffectedBlock,
	AffectedScript,
	AIModel,
	AIProvider,
	AITurnStep,
	ChatMessage,
} from "@/components/ai/types";

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
	readonly isLoadingSession = ref(false);
	// only the newest load may commit; older responses are stale
	private loadSessionEpoch = 0;
	// target of the newest in-flight load; refreshes follow it, not the current session
	private pendingSessionId: string | null = null;
	// orders the user's session choices (switch/new/delete); refreshes don't count
	private sessionIntentEpoch = 0;
	// in-flight new_ai_session calls; a "reselect" during one must cancel it
	private pendingSessionCreates = 0;

	private invalidateSessionLoads() {
		this.loadSessionEpoch++;
		this.pendingSessionId = null;
		this.isLoadingSession.value = false;
	}
	// This page's chat sessions (most recent first) — the panel's session switcher.
	readonly sessions = ref<Array<{ name: string; title: string | null }>>([]);
	readonly availableModels = ref<AIProvider[]>([]);
	readonly selectedModel = useLocalStorage("ai-selected-model", "");

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

	/** Accept one page_yaml chunk for the canvas. Dedupes replayed chunks by stream
	 * offset, and refetches the server buffer when a gap shows we missed some. */
	private acceptPageYamlChunk(data: { chunk?: string; offset?: number }): void {
		if (typeof data.offset === "number") {
			const have = this.pageStreamContent.value.length;
			if (data.offset < have) return;
			if (data.offset > have) {
				this.syncActiveBuild();
				return;
			}
		}
		this.beginCanvasBuild();
		this.previewUnconfirmed = true;
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
		if (this.pageId.value !== pid) return;
		if (!build?.yaml) return;
		if (build.yaml.length <= this.pageStreamContent.value.length) return;
		this.beginCanvasBuild();
		this.pageStreamContent.value = build.yaml;
		this.scheduleStreamRender();
	}

	readonly isImprovingPrompt = ref(false);

	/** One cheap completion that sharpens the composer draft in place — the user
	 * still reads and edits it before sending. */
	improvePrompt = async () => {
		const draft = this.prompt.value.trim();
		if (!draft || this.isImprovingPrompt.value) return;
		this.isImprovingPrompt.value = true;
		try {
			const improved = (await createResource({ url: "builder.ai.api.improve_prompt" }).submit({
				prompt: draft,
				model: this.selectedModel.value,
			})) as string;
			if (improved) this.prompt.value = improved;
		} catch (error) {
			toast.error(error instanceof Error ? error.message : "Could not improve the prompt");
		} finally {
			this.isImprovingPrompt.value = false;
		}
	};
	// Compact display line for a card-composed reply (set by selectOption).
	private pendingDisplayText: string | null = null;

	private readonly pageStreamContent = ref(""); // accumulates kind="page_yaml" chunks
	// True while the canvas shows a streamed preview that no authoritative
	// tool_batch has replaced — if the turn ends in that state (failed generation,
	// cancel), the preview is dead weight and the canvas must resync to the draft.
	private previewUnconfirmed = false;
	private readonly summaryContent = ref(""); // accumulates summary chunks
	/** The in-flight turn's timeline, mirrored onto the pending message as it grows. */
	private readonly liveSteps = ref<AITurnStep[]>([]);
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
	// Every enabled provider's models, in the order the registry returns them —
	// which providers exist is site configuration (Builder AI Provider), not a
	// fixed list, so the picker must not name one.
	readonly currentProviderModels = computed(() => this.availableModels.value.flatMap((p) => p.models || []));
	readonly selectedBlocks = computed<Block[]>(
		() => (this.canvasStore.activeCanvas?.selectedBlocks || []) as Block[],
	);
	/** Blocks the user explicitly attached to the next message — canvas selection
	 * by itself sends nothing. */
	readonly attachedBlocks = ref<{ id: string; label: string }[]>([]);
	/** Currently selected canvas blocks not yet attached — what the "+" chip offers. */
	readonly attachableBlocks = computed<Block[]>(() => {
		const attached = new Set(this.attachedBlocks.value.map((b) => b.id));
		return this.selectedBlocks.value.filter((b) => b.blockId && !attached.has(b.blockId));
	});

	attachSelection = () => {
		for (const block of this.attachableBlocks.value) {
			this.attachedBlocks.value.push({
				id: block.blockId,
				label: block.getBlockDescription?.() || block.blockName || block.element || "block",
			});
		}
	};

	detachBlock = (id: string) => {
		this.attachedBlocks.value = this.attachedBlocks.value.filter((b) => b.id !== id);
	};
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
	/** The picked model has no key behind it, so sending would only produce a server
	 * error. Per-model, not per-site: with two providers configured, one can be
	 * keyless while the site as a whole looks set up. */
	readonly selectedModelUnusable = computed(() => {
		const model = this.currentProviderModels.value.find((m) => m.name === this.selectedModel.value);
		return !!model && model.ready === false;
	});
	readonly canSubmit = computed(
		() =>
			!!this.prompt.value.trim() &&
			!this.isSubmitting.value &&
			!!this.selectedModel.value &&
			!this.selectedModelUnusable.value,
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
			this.sessionIntentEpoch++;
			this.invalidateSessionLoads();
			this.sessionId.value = "";
			this.sessions.value = [];
			this.messages.value = [];
			if (newPageId === "new") return;
			await this.loadSession();
			// A build may be mid-stream on this page (opened from another chat's link,
			// or a refresh mid-generation): replay the buffered stream as live preview.
			this.syncActiveBuild();
		});

		// loadSession stands down until AI is known to be on — but that answer only
		// arrives once ai_setup_state (and Builder Settings) resolve, which is AFTER
		// mount runs. Without this retry the very first load bails and never comes
		// back, so the panel settles on an empty "New chat" with the real
		// conversation still sitting in the database and no history to switch to.
		watch(
			() => this.builderStore.isAIEnabled,
			(enabled) => {
				if (enabled && !this.sessionId.value) this.loadSession();
			},
		);
	}

	private get handlers(): AIChatHandlers {
		return {
			onProgress: this.onProgress,
			onStream: this.onStream,
			onToolBatch: this.onToolBatch,
			onClarify: this.onClarify,
			onComplete: this.onComplete,
			onError: this.onError,
			onStep: this.onStep,
			onRefetch: this.onRefetch,
		};
	}

	resetTransientState() {
		this.clearStreamRenderTimer();
		this.endCanvasBuild();
		this.progressMessage.value = "";
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.liveSteps.value = [];
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
			nextTick(() => this.canvasStore.activeCanvas?.followBuildEdge());
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

	// scrolling a display:none container (closed tab) is a no-op; park and replay
	private pendingScrollToBottom = false;

	private scrollToBottom() {
		nextTick(() => {
			const el = this.messageContainer.value;
			if (!el || el.clientHeight === 0) {
				this.pendingScrollToBottom = true;
				return;
			}
			el.scrollTop = el.scrollHeight;
		});
	}

	flushPendingScroll = () => {
		if (!this.pendingScrollToBottom) return;
		this.pendingScrollToBottom = false;
		this.scrollToBottom();
	};

	/** Load a chat session: the given one, else the current one, else the page's
	 * most recently used (the server creates the first). A page can hold several
	 * parallel sessions — see switchSession/newSession. */
	async loadSession(sessionId?: string) {
		if (!this.pageId.value || !this.builderStore.isAIEnabled || this.isUnsavedPage.value) return;
		const target = sessionId || this.pendingSessionId || this.sessionId.value || undefined;
		const epoch = ++this.loadSessionEpoch;
		const pageId = this.pageId.value;
		this.pendingSessionId = target ?? null;
		this.isLoadingSession.value = true;
		try {
			const result = await createResource({
				url: "builder.ai.api.get_ai_session",
				makeParams: () => ({
					page_id: pageId,
					model: this.selectedModel.value,
					session_id: target,
				}),
			}).submit();
			if (epoch !== this.loadSessionEpoch || this.pageId.value !== pageId) return;
			const session = result as { session_id: string; messages: ChatMessage[] };
			this.sessionId.value = session.session_id;
			this.messages.value = (session.messages || []).map(
				(m) => ({ ...m, role: m.role === "user" ? "user" : "assistant" } as ChatMessage),
			);
			this.scrollToBottom();
			this.loadSessions();
		} finally {
			if (epoch === this.loadSessionEpoch) {
				this.isLoadingSession.value = false;
				this.pendingSessionId = null;
			}
		}
	}

	/** Refresh the session-switcher list (fire-and-forget; the panel renders it). */
	loadSessions = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const pageId = this.pageId.value;
		const rows = await createResource({ url: "builder.ai.api.list_page_ai_sessions" })
			.submit({ page_id: pageId })
			.catch(() => null);
		if (rows && this.pageId.value === pageId)
			this.sessions.value = rows as Array<{ name: string; title: string | null }>;
	};

	switchSession = async (sessionId: string) => {
		// reselecting the current chat is a no-op only when nothing else is pending
		if (
			!sessionId ||
			(sessionId === this.sessionId.value && !this.pendingSessionId && !this.pendingSessionCreates)
		)
			return;
		this.sessionIntentEpoch++;
		this.resetTransientState();
		await this.loadSession(sessionId);
		this.scrollToBottom();
	};

	newSession = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const intent = ++this.sessionIntentEpoch;
		this.invalidateSessionLoads();
		const pageId = this.pageId.value;
		this.pendingSessionCreates++;
		try {
			const result = await createResource({ url: "builder.ai.api.new_ai_session" }).submit({
				page_id: pageId,
				model: this.selectedModel.value,
			});
			// a later choice (another chat, another page) beats this create
			if (intent !== this.sessionIntentEpoch || this.pageId.value !== pageId) return;
			this.resetTransientState();
			// loads started during the round-trip above carry a valid epoch; void them
			this.invalidateSessionLoads();
			this.sessionId.value = (result as { session_id: string }).session_id;
			this.messages.value = [];
			this.loadSessions();
		} finally {
			this.pendingSessionCreates--;
		}
	};

	deleteSession = async () => {
		if (!this.sessionId.value) return;
		if (!(await confirm("Delete this chat? Its messages are removed; the page itself is untouched."))) return;
		const intent = ++this.sessionIntentEpoch;
		const pageId = this.pageId.value;
		await createResource({ url: "builder.ai.api.delete_ai_session" })
			.submit({ session_id: this.sessionId.value })
			.catch(() => null);
		if (intent !== this.sessionIntentEpoch || this.pageId.value !== pageId) return;
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

	/** The turn's headline status ("Thinking with Claude Sonnet 5"), for the panel
	 * header only. What the turn is DOING belongs to the timeline now — writing it
	 * into the bubble as well just says the same thing twice. */
	onProgress = (data: { message?: string; session_id?: string }) => {
		if (this.isForeignSession(data)) return;
		this.isSubmitting.value = true;
		this.progressMessage.value = data.message || this.progressMessage.value;
	};

	/** One timeline entry, upserted by id: the model thinking, a tool running, or the
	 * narration it wrote before moving on. A "text" step is also the signal that the
	 * round is over — whatever has been streaming becomes part of the timeline and the
	 * live answer resets for the next round. */
	onStep = (data: AITurnStep & { session_id?: string }) => {
		if (this.isForeignSession(data) || typeof data.id !== "number") return;
		this.isSubmitting.value = true;
		const { session_id, page_id, ...step } = data as Record<string, any>;
		if (step.kind === "text") this.summaryContent.value = "";
		const index = this.liveSteps.value.findIndex((s) => s.id === step.id);
		if (index === -1) this.liveSteps.value.push(step as AITurnStep);
		else this.liveSteps.value[index] = { ...this.liveSteps.value[index], ...step };
		if (step.kind === "tool" && step.summary && step.status === "running") {
			this.progressMessage.value = step.summary;
		}
		this.syncPendingSteps();
		this.scrollToBottom();
	};

	/** Mirror the live timeline (and whatever is streaming) onto the pending message,
	 * so the renderer only ever reads a message — live and reloaded turns take the
	 * exact same path. */
	private syncPendingSteps() {
		this.replacePendingAssistant(this.summaryContent.value || "", {
			status: "running",
			steps: [...this.liveSteps.value],
		});
	}

	onStream = (data: {
		chunk?: string;
		kind?: string;
		session_id?: string;
		offset?: number;
		replace?: boolean;
	}) => {
		if (!data.chunk && !data.replace) return;
		if (this.isForeignSession(data)) {
			// Another chat on this page is generating: the canvas is page-level, so
			// paint its preview, but keep its chat text out of this session.
			if (data.kind === "page_yaml") this.acceptPageYamlChunk(data);
			return;
		}
		this.isSubmitting.value = true;
		if (data.kind === "page_yaml") {
			this.acceptPageYamlChunk(data);
			return;
		}
		if (data.kind === "reasoning") {
			// Reasoning belongs to the thinking step that is currently open.
			const thinking = [...this.liveSteps.value].reverse().find((s) => s.kind === "thinking");
			if (thinking) thinking.text = (thinking.text || "") + data.chunk;
			return;
		}
		// `replace` means the server is correcting what it already sent (a guard
		// rewrote the summary, or a retry is re-sending the round).
		this.summaryContent.value = data.replace ? data.chunk || "" : this.summaryContent.value + data.chunk;
		this.syncPendingSteps();
		this.scrollToBottom();
	};

	/** A server tool changed state the canvas only loads at editor start. Refetch
	 * exactly what changed so mid-turn results render without a manual refresh:
	 * theme variables (var(--id) styles), the evaluated page data (repeater
	 * previews), or the page doc (route/meta). NOT session-scoped — this state is
	 * page/site-level, so any chat's turn should refresh it. */
	onRefetch = async (data: { resources?: string[] }) => {
		const resources = data.resources || [];
		if (resources.includes("variables")) {
			builderTokens.reload();
		}
		if (resources.includes("page_data") || resources.includes("page")) {
			const page = await this.pageStore.fetchActivePage(this.pageId.value).catch(() => null);
			if (page) {
				this.pageStore.activePage = page;
				if (resources.includes("page_data")) await this.pageStore.setPageData(page);
			}
		}
	};

	onToolBatch = (data: {
		session_id?: string;
		operations?: Array<{ tool_name: string; args: Record<string, any> }>;
	}) => {
		// Cancel any pending throttled stream render so it can't fire AFTER and clobber
		// the authoritative apply below with stale partial YAML.
		this.clearStreamRenderTimer();
		if (!data.operations?.length) return;
		this.previewUnconfirmed = false;
		for (const op of data.operations) {
			this.dispatcher.trackAffectedItem(op.tool_name, op.args); // track before apply (remove_block)
			try {
				this.dispatcher.applyToolOperation(op.tool_name, op.args);
			} catch (e) {
				console.warn(`[AI agent] tool "${op.tool_name}" failed:`, e);
			}
		}
		const followId = this.followTargetIn(data.operations);
		if (followId) nextTick(() => this.canvasStore.activeCanvas?.followBlock(followId));
		// Don't overwrite the bubble with a static "Applying N changes…" — the loop emits
		// a per-round progress note (the model's words, or a "Updated N blocks" summary)
		// right after each batch, which is what the user actually sees update.
		this.scrollToBottom();
	};

	/** The batch's last touched block, for the canvas to pan into view. Whole-tree
	 * rewrites (generate_page/set_page_blocks) have no single locus; skip those. */
	private followTargetIn(operations: Array<{ tool_name: string; args: Record<string, any> }>) {
		for (let i = operations.length - 1; i >= 0; i--) {
			const { tool_name, args } = operations[i];
			if (tool_name === "add_block") {
				return ((args.block_json as Record<string, any>)?.blockId || args.parent_block_id) as string;
			}
			if (tool_name === "update_block" || tool_name === "move_block") return args.block_id as string;
			if (tool_name === "update_blocks") {
				if (Array.isArray(args.patches)) {
					return (args.patches as Record<string, any>[]).at(-1)?.block_id as string;
				}
				return ((args.block_ids as string[]) || []).at(-1);
			}
		}
		return null;
	}

	onComplete = async (data: { message?: string; session_id?: string }) => {
		if (this.isForeignSession(data)) {
			// The other chat's build on this page finished; the authoritative
			// tool_batch already replaced the streamed preview.
			this.endCanvasBuild();
			return;
		}
		this.clearStreamRenderTimer();
		this.endCanvasBuild(this.previewUnconfirmed);
		this.previewUnconfirmed = false;
		if (this.submittedForPageId && this.submittedForPageId !== this.pageId.value) {
			this.submittedForPageId = null;
			return;
		}
		this.submittedForPageId = null;
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.progressMessage.value = data.message || "Done";
		// the session this turn belongs to; the user may switch chats mid-await below
		const completedSession = data.session_id || this.sessionId.value;

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
		this.liveSteps.value = [];
		this.dispatcher.reset();

		const localMeta = { ...meta };
		if (
			completedSession &&
			(localMeta.affectedBlocks?.length || localMeta.affectedScripts?.length || localMeta.undoScripts?.length)
		) {
			createResource({ url: "builder.ai.api.update_session_message_metadata" })
				.submit({ session_id: completedSession, metadata: localMeta })
				.catch(() => null);
		}

		await this.loadSession();

		// Re-apply client-only metadata in case the server hasn't flushed it yet —
		// but only onto the turn's own session, not one switched to meanwhile.
		if (
			this.sessionId.value === completedSession &&
			(localMeta.affectedBlocks?.length ||
				localMeta.affectedScripts?.length ||
				localMeta.undoScripts?.length)
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
		this.endCanvasBuild(this.previewUnconfirmed);
		this.previewUnconfirmed = false;
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.progressMessage.value = "";
		this.replacePendingAssistant(data.message || "Request failed", { status: "error" });
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.liveSteps.value = [];
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
		this.endCanvasBuild(this.previewUnconfirmed);
		this.previewUnconfirmed = false;
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.progressMessage.value = "";
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.liveSteps.value = [];

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
			if (res?.resumed) this.beginResumedTurn();
		} catch (e: any) {
			toast.error(e?.messages?.[0] || "Could not apply the change");
		}
	};

	/** Running state for a turn the server started itself, after a confirmed action.
	 * Must run after loadSession, which would drop the placeholder. */
	beginResumedTurn = () => {
		const assistantMessage = buildLocalMessage("assistant", "", { status: "running" });
		this.messages.value.push(assistantMessage);
		this.pendingAssistantId.value = assistantMessage.id;
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.liveSteps.value = [];
		this.dispatcher.reset();
		this.isSubmitting.value = true;
		this.scrollToBottom();
	};

	/** Ask the backend to abort the in-flight turn at its next stream chunk.
	 * Anthropic/OpenRouter stop billing once the stream is closed. The backend's
	 * cancelled `complete` event lands only after the next chunk + a round trip,
	 * so we show "Cancelling" locally right away for instant feedback; that event
	 * (or onError/onClarify) clears isCancelling when the turn actually ends. */
	cancel = async () => {
		if (!this.sessionId.value || !this.isSubmitting.value || this.isCancelling.value) return;
		this.isCancelling.value = true;
		this.progressMessage.value = "Cancelling…";
		this.replacePendingAssistant("Cancelling…", { status: "running" });
		const resetStuckCancel = async () => {
			if (!this.isCancelling.value) return;
			this.endCanvasBuild(!!this.pageStreamContent.value);
			this.resetTransientState();
			await this.loadSession();
			toast.info("That run is no longer active.");
		};
		try {
			const res: any = await createResource({ url: "builder.ai.api.cancel" }).submit({
				session_id: this.sessionId.value,
			});
			// No live turn holds the session lock (it crashed or timed out): nothing
			// will ever acknowledge the flag, so resolve the UI now.
			if (res?.status === "not_running") await resetStuckCancel();
		} catch {
			// Ignore — the user will see the event when it arrives.
		}
		// Watchdog: a wedged run (e.g. a stalled provider connection) can't reach its
		// next cancellation check. Don't leave "Cancelling…" up forever.
		setTimeout(resetStuckCancel, 20000);
	};

	submitPrompt = async () => {
		if (!this.canSubmit.value || !this.pageId.value || this.isUnsavedPage.value) return;
		// submitting pins the current chat: a still-pending create must not replace it
		this.sessionIntentEpoch++;

		const userText = this.prompt.value.trim();
		this.prompt.value = "";
		this.submittedForPageId = this.pageId.value;
		if (!this.sessionId.value) await this.loadSession();

		// Only explicitly attached blocks travel with the message.
		const selectedBlockContext = this.attachedBlocks.value.map((b) => ({ id: b.id, label: b.label }));
		const selectedIds = this.attachedBlocks.value.map((b) => b.id);
		this.attachedBlocks.value = [];
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
		// Empty on purpose: the panel shows a "Thinking" shimmer for a running turn
		// with no timeline yet, and the first step replaces it a moment later.
		const assistantMessage = buildLocalMessage("assistant", "", { status: "running" });
		this.messages.value.push(userMessage, assistantMessage);
		this.pendingAssistantId.value = assistantMessage.id;
		this.scrollToBottom();
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.liveSteps.value = [];
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

	/** Refetch the picker's models. Called on mount and again whenever Settings
	 * closes: connecting a provider or enabling a model happens over there, and
	 * without this the picker keeps whatever list it was given at mount. */
	loadModels() {
		createResource({
			url: "builder.ai.api.get_ai_models",
			auto: true,
			onSuccess: (data: AIProvider[]) => {
				this.availableModels.value = data;
			},
		});
	}

	async mount() {
		if (this.pageId.value)
			attachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
		this.loadModels();
		await this.loadSession();
	}

	unmount() {
		if (this.pageId.value)
			detachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
	}
}
