import type Block from "@/block";
import type { CardSubmission } from "@/components/ai/cardAnswers";
import builderTokens from "@/data/builderToken";
import { type AIChatHandlers, attachAIChatListeners, detachAIChatListeners } from "@/components/ai/realtime";
import { readDraft, RunEvents, type SendEnvelope, writeDraft } from "@/components/ai/lifecycle";
import { type PageCanvas, ToolDispatcher } from "@/components/ai/toolDispatch";
import type {
	AIProvider,
	AIRun,
	AIRunEvent,
	AISession,
	AITurnStep,
	ChatMessage,
} from "@/components/ai/types";
import { buildLocalMessage } from "@/components/ai/yaml";
import type BuilderCanvas from "@/components/BuilderCanvas.vue";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { confirm, getErrorMessage } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { createResource, toast } from "frappe-ui";
import { computed, inject, nextTick, ref, shallowRef, watch } from "vue";
import { useRoute } from "vue-router";

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
	// Bob edits the page, so everything lands here even while a component is open
	private readonly pageCanvas: PageCanvas = inject(
		"pageCanvas",
		shallowRef<InstanceType<typeof BuilderCanvas> | null>(null),
	);
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
	readonly isSwitchingSession = ref(false);
	readonly isReverting = ref(false);
	readonly isRefreshingPage = ref(false);
	readonly activeRun = ref<AIRun | null>(null);
	private readonly events = new RunEvents();
	private readonly observedRuns = new Map<string, string>();
	private readonly retryEnvelope = ref<SendEnvelope | null>(null);
	private readonly stopWatchers: Array<() => void> = [];
	private disposed = false;
	private mounted = false;
	private restoringDraft = false;
	private blankSessionSelected = false;
	private reconcilePromise: Promise<void> | null = null;
	private reconcileAgain = false;
	private pageNeedsRefresh = false;
	private pageRefreshVersion = 0;
	private reconcileFailures = 0;
	private reconcileTimer: ReturnType<typeof setTimeout> | undefined;
	private buildSyncPromise: Promise<void> | null = null;
	private buildEpoch = 0;
	private generationId = "";
	private generationRunId = "";
	private generationSequence = -1;
	private readonly retiredGenerations = new Set<string>();
	private readonly affectedByRun = new Map<string, Record<string, any>>();
	// only the newest load may commit; older responses are stale
	private loadSessionEpoch = 0;
	// target of the newest in-flight load; refreshes follow it, not the current session
	private pendingSessionId: string | null = null;
	// orders the user's session choices (switch/new/delete); refreshes don't count
	private sessionIntentEpoch = 0;
	// turns started from this panel; liveSend is the one whose run call is still out
	private turnCount = 0;
	private liveSend = 0;
	// a blank chat can't tell its own turn's events from another chat's until run
	// names the session it created, so they wait here and replay once it does
	private heldEvents: Array<{ runId: string; replay: () => void }> = [];
	private readonly foreignEvents = new Map<string, Array<{ data: AIRunEvent; replay: () => void }>>();
	private readonly stepSequences = new Map<number, number>();
	private cancelOnceKnown = false;

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
		// Silence is not proof of completion; ask the server before releasing a preview.
		this.buildQuietTimer = setTimeout(() => this.requestReconciliation(true), 45000);
	}

	private endCanvasBuild() {
		if (this.buildQuietTimer) {
			clearTimeout(this.buildQuietTimer);
			this.buildQuietTimer = null;
		}
		if (!this.builderStore.aiBuildingCanvas) return;
		this.builderStore.aiBuildingCanvas = false;
	}

	/** Accept one page_yaml chunk for the canvas. Dedupes replayed chunks by stream
	 * offset, and refetches the server buffer when a gap shows we missed some. */
	private acceptPageYamlChunk(
		data: AIRunEvent & { generation_id?: string; chunk?: string; offset?: number },
	): void {
		if (!this.selectGeneration(data.run_id, data.generation_id, data.seq)) return;
		if (typeof data.offset === "number") {
			const have = this.pageStreamContent.value.length;
			if (data.offset < have) return;
			if (data.offset > have) {
				void this.syncActiveBuild().catch(() => this.requestReconciliation(true));
				return;
			}
		}
		this.beginCanvasBuild();
		this.pageStreamContent.value += data.chunk || "";
		this.scheduleStreamRender();
	}

	/** A mid-build page load: replay the in-flight generation stream from the
	 * server's buffer so the canvas shows the live build, not the stale draft. */
	private selectGeneration(runId: string, generationId?: string, seq = -1) {
		if (!generationId || this.events.finished(runId) || this.retiredGenerations.has(generationId))
			return false;
		if (this.generationId === generationId && this.generationRunId === runId) return true;
		if (this.generationRunId === runId && seq >= 0 && seq < this.generationSequence) return false;
		this.resetGeneration();
		this.generationId = generationId;
		this.generationRunId = runId;
		this.generationSequence = seq;
		return true;
	}

	private resetGeneration() {
		this.buildEpoch++;
		if (this.generationId) this.retiredGenerations.add(this.generationId);
		this.clearStreamRenderTimer();
		this.generationId = "";
		this.generationRunId = "";
		this.generationSequence = -1;
		this.pageStreamContent.value = "";
	}

	private syncActiveBuild(): Promise<void> {
		if (this.buildSyncPromise) return this.buildSyncPromise;
		this.buildSyncPromise = this.loadActiveBuild().finally(() => {
			this.buildSyncPromise = null;
		});
		return this.buildSyncPromise;
	}

	private async loadActiveBuild() {
		const pid = this.pageId.value;
		const epoch = this.buildEpoch;
		if (!pid || pid === "new" || this.disposed) return;
		const build: any = await createResource({ url: "builder.ai.api.get_active_build" }).submit({
			page_id: pid,
		});
		if (this.disposed || this.pageId.value !== pid || epoch !== this.buildEpoch) return;
		if (!build?.generation_id || !build?.run_id) {
			if (this.generationId) {
				this.pageNeedsRefresh = true;
				this.resetGeneration();
			}
			return;
		}
		if (!this.selectGeneration(build.run_id, build.generation_id)) return;
		if (!build.yaml || build.yaml.length < this.pageStreamContent.value.length) return;
		this.beginCanvasBuild();
		this.pageStreamContent.value = build.yaml;
		this.scheduleStreamRender();
	}

	// Compact display line for a card-composed reply (set by selectOption).
	private pendingDisplayText: string | null = null;
	private pendingCardAnswer: CardSubmission | null = null;

	private readonly pageStreamContent = ref(""); // accumulates kind="page_yaml" chunks
	private readonly summaryContent = ref(""); // accumulates summary chunks
	/** The in-flight turn's timeline, mirrored onto the pending message as it grows. */
	private readonly liveSteps = ref<AITurnStep[]>([]);
	private readonly pendingAssistantId = ref<string | null>(null);
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
	readonly isVisionModel = computed(
		() => this.currentProviderModels.value.find((m) => m.name === this.selectedModel.value)?.vision ?? false,
	);
	/** The picked model has no key behind it, so sending would only produce a server
	 * error. Per-model, not per-site: with two providers configured, one can be
	 * keyless while the site as a whole looks set up. */
	readonly selectedModelUnusable = computed(() => {
		const model = this.currentProviderModels.value.find((m) => m.name === this.selectedModel.value);
		return !!this.selectedModel.value && (!model || model.ready === false);
	});
	/** A turn saves the canvas first, and with a component open on the canvas that
	 * would write the component over the page draft. */
	readonly isEditingPage = computed(() => this.canvasStore.editingMode === "page");
	readonly canSubmit = computed(
		() =>
			!!this.prompt.value.trim() &&
			!this.isSubmitting.value &&
			!this.isSwitchingSession.value &&
			!this.isReverting.value &&
			!this.isRefreshingPage.value &&
			this.isEditingPage.value &&
			!!this.selectedModel.value &&
			!this.selectedModelUnusable.value,
	);

	constructor() {
		this.dispatcher = new ToolDispatcher(this.pageStore, this.pageCanvas);

		this.stopWatchers.push(
			watch(
				this.currentProviderModels,
				(models) => {
					if (models.length && !this.selectedModel.value) {
						this.selectedModel.value = models[0].name;
					}
				},
				{ immediate: true },
			),
		);

		this.stopWatchers.push(
			watch(this.pageId, async (newPageId, oldPageId) => {
				if (oldPageId) detachAIChatListeners(this.builderStore.realtime, oldPageId, this.handlers);
				if (newPageId) attachAIChatListeners(this.builderStore.realtime, newPageId, this.handlers);
				this.resetTransientState();
				this.resetGeneration();
				this.endCanvasBuild();
				this.events.clear();
				this.observedRuns.clear();
				this.retiredGenerations.clear();
				// Sessions are page-scoped: never carry one across a page switch.
				this.sessionIntentEpoch++;
				this.invalidateSessionLoads();
				this.sessionId.value = "";
				this.sessions.value = [];
				this.messages.value = [];
				this.restoreSessionChoice();
				this.restoreComposer();
				if (!newPageId || newPageId === "new") return;
				await this.reconcile();
			}),
		);

		// loadSession stands down until AI is known to be on — but that answer only
		// arrives once ai_setup_state (and Builder Settings) resolve, which is AFTER
		// mount runs. Without this retry the very first load bails and never comes
		// back, so the panel settles on an empty "New chat" with the real
		// conversation still sitting in the database and no history to switch to.
		this.stopWatchers.push(
			watch(
				() => this.builderStore.isAIEnabled,
				(enabled) => {
					if (enabled && !this.sessionId.value) this.requestReconciliation();
				},
			),
		);
		this.restoreSessionChoice();
		this.restoreComposer();
		this.stopWatchers.push(
			watch(
				[
					this.prompt,
					this.imageData,
					this.imagePreviewUrl,
					this.imageFileName,
					this.attachedBlocks,
					this.retryEnvelope,
				],
				() => this.persistComposer(),
				{ deep: true, flush: "sync" },
			),
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
		this.liveSend = 0;
		this.heldEvents = [];
		this.cancelOnceKnown = false;
		this.progressMessage.value = "";
		this.summaryContent.value = "";
		this.liveSteps.value = [];
		this.pendingAssistantId.value = null;
		this.dispatcher.reset();
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.activeRun.value = null;
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
			nextTick(() => this.pageCanvas.value?.followBuildEdge());
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
	private scrollFrame = 0;

	/** At most once a frame: streaming calls this per token, and each scroll forces
	 * a layout. The frame lands after Vue has patched the DOM. */
	private scrollToBottom() {
		if (this.scrollFrame) return;
		this.scrollFrame = requestAnimationFrame(() => {
			this.scrollFrame = 0;
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

	private composerKey() {
		return `composer:${this.pageId.value}:${this.sessionId.value || "new"}`;
	}

	private restoreSessionChoice() {
		const selected = readDraft<string>(`selected:${this.pageId.value}`);
		this.sessionId.value = selected || "";
		this.blankSessionSelected = selected === "";
	}

	private persistComposer() {
		if (this.restoringDraft || this.disposed) return;
		writeDraft(this.composerKey(), {
			prompt: this.prompt.value,
			imageData: this.imageData.value,
			imagePreviewUrl: this.imagePreviewUrl.value,
			imageFileName: this.imageFileName.value,
			blocks: this.attachedBlocks.value,
			displayText: this.pendingDisplayText,
			cardAnswer: this.pendingCardAnswer,
			retryEnvelope: this.retryEnvelope.value,
		});
	}

	private restoreComposer() {
		const draft = readDraft<Partial<SendEnvelope> & { retryEnvelope?: SendEnvelope }>(this.composerKey());
		this.restoringDraft = true;
		this.retryEnvelope.value = draft?.retryEnvelope || null;
		// An interrupted HTTP request is also a retryable draft after refresh.
		const content = draft?.prompt ? draft : draft?.retryEnvelope || draft;
		this.prompt.value = content?.prompt || "";
		this.imageData.value = content?.imageData || null;
		this.imagePreviewUrl.value = content?.imagePreviewUrl || null;
		this.imageFileName.value = content?.imageFileName || "";
		this.attachedBlocks.value = content?.blocks || [];
		this.pendingDisplayText = content?.displayText || null;
		this.pendingCardAnswer = content?.cardAnswer || null;
		this.restoringDraft = false;
	}

	private hydrateSession(session: AISession) {
		if (session.deleted_session) {
			this.retryEnvelope.value = null;
			this.sessionIntentEpoch++;
			toast.info("This chat was deleted in another tab. Start a new chat to continue.");
		}

		const previousRun = this.activeRun.value?.run_id;
		const run = session.active_run;
		const sameRun = !!run && run.run_id === previousRun;
		const pending = sameRun ? this.messages.value.find((m) => m.id === this.pendingAssistantId.value) : null;
		if (previousRun && !sameRun && session.session_id === this.sessionId.value)
			this.events.finish(previousRun);
		if (session.session_id !== this.sessionId.value) {
			this.sessionId.value = session.session_id;
			this.restoreComposer();
		}
		writeDraft(`selected:${this.pageId.value}`, session.session_id);
		this.messages.value = (session.messages || []).map(
			(m) =>
				({
					...m,
					role: m.role === "user" ? "user" : "assistant",
					metadata: {
						...m.metadata,
						...(m.role === "assistant" ? this.affectedByRun.get(m.metadata?.runId) : {}),
					},
				}) as ChatMessage,
		);
		this.activeRun.value = run || null;
		this.isSubmitting.value = !!run;
		if (!sameRun) {
			this.summaryContent.value = "";
			this.liveSteps.value = [];
			this.dispatcher.reset();
			this.stepSequences.clear();
			this.isCancelling.value = false;
			this.progressMessage.value = run?.status === "queued" ? "Queued…" : "";
		}
		this.pendingAssistantId.value = null;
		if (run) {
			this.observedRuns.set(session.session_id, run.run_id);
			const assistant =
				pending || buildLocalMessage("assistant", "", { status: "running", run_id: run.run_id });
			this.messages.value.push(assistant);
			this.pendingAssistantId.value = assistant.id;
		}
		this.scrollToBottom();
	}

	/** Load a chat session: the given one, else the current one, else the page's
	 * most recently used, or a blank chat when there is none. A page can hold
	 * several parallel sessions; see switchSession/newSession. */
	async loadSession(sessionId?: string): Promise<boolean> {
		if (this.disposed || !this.pageId.value || !this.builderStore.isAIEnabled || this.isUnsavedPage.value)
			return false;
		const target = sessionId || this.pendingSessionId || this.sessionId.value || undefined;
		const pendingRequest =
			!sessionId && this.retryEnvelope.value?.attempted ? this.retryEnvelope.value : null;
		if (!target && this.blankSessionSelected && !pendingRequest) {
			this.loadSessions();
			return true;
		}
		const epoch = ++this.loadSessionEpoch;
		const pageId = this.pageId.value;
		const intent = this.sessionIntentEpoch;
		this.pendingSessionId = target ?? null;
		this.isLoadingSession.value = true;
		try {
			const result = await createResource({
				url: "builder.ai.api.get_ai_session",
				makeParams: () => ({
					page_id: pageId,
					model: this.selectedModel.value,
					session_id: target,
					...(pendingRequest ? { request_id: pendingRequest.requestId } : {}),
				}),
			}).submit();
			if (
				this.disposed ||
				epoch !== this.loadSessionEpoch ||
				this.pageId.value !== pageId ||
				intent !== this.sessionIntentEpoch
			)
				return false;
			const session = result as AISession;
			// An unknown first request must not select an unrelated latest chat.
			if (pendingRequest && !pendingRequest.sessionId && !session.request_run) return true;
			if (session.request_run && this.retryEnvelope.value) {
				const unchanged = this.sendEnvelope().requestId === this.retryEnvelope.value.requestId;
				this.retryEnvelope.value = null;
				if (unchanged) {
					this.prompt.value = "";
					this.attachedBlocks.value = [];
					this.pendingDisplayText = null;
					this.pendingCardAnswer = null;
					this.clearImage();
				}
				this.persistComposer();
				if (session.session_id !== this.sessionId.value) {
					writeDraft(`composer:${pageId}:${session.session_id}`, readDraft(this.composerKey()));
					writeDraft(this.composerKey(), null);
				}
			}
			this.hydrateSession(session);
			this.blankSessionSelected = !session.session_id;
			this.loadSessions();
			return true;
		} finally {
			if (epoch === this.loadSessionEpoch) {
				this.isLoadingSession.value = false;
				this.pendingSessionId = null;
			}
		}
	}

	/** One in-flight read, with bounded backoff. Idle polling also discovers work in another tab. */
	private scheduleReconciliation(delay?: number) {
		clearTimeout(this.reconcileTimer);
		if (!this.mounted || this.disposed) return;
		const interval = this.isSubmitting.value || this.builderStore.aiBuildingCanvas ? 5000 : 15000;
		this.reconcileTimer = setTimeout(
			() => this.reconcile(),
			delay ?? Math.min(30000, interval * 2 ** this.reconcileFailures),
		);
	}

	private requestReconciliation = (refreshPage = false) => {
		if (this.disposed) return;
		this.pageNeedsRefresh ||= refreshPage;
		if (refreshPage) this.pageRefreshVersion++;
		if (this.reconcilePromise) this.reconcileAgain = true;
		else void this.reconcile();
	};

	private onReconnect = () => this.requestReconciliation(true);
	private onVisibility = () => {
		if (document.visibilityState === "visible") this.requestReconciliation(true);
	};

	reconcile = (): Promise<void> => {
		if (this.reconcilePromise) return this.reconcilePromise;
		if (this.disposed || this.liveSend || this.isSwitchingSession.value || this.isReverting.value) {
			this.scheduleReconciliation();
			return Promise.resolve();
		}
		clearTimeout(this.reconcileTimer);
		this.reconcilePromise = this.reconcileState()
			.catch(() => {
				this.reconcileFailures = Math.min(this.reconcileFailures + 1, 3);
			})
			.finally(() => {
				this.reconcilePromise = null;
				const again = this.reconcileAgain;
				this.reconcileAgain = false;
				this.scheduleReconciliation(again ? 0 : undefined);
			});
		return this.reconcilePromise;
	};

	private async reconcileState() {
		const pageId = this.pageId.value;
		const intent = this.sessionIntentEpoch;
		const hadRun = !!this.activeRun.value;
		const before = this.messages.value
			.filter((m) => m.id !== this.pendingAssistantId.value)
			.map((m) => m.id)
			.join();
		if (!(await this.loadSession())) return;
		this.reconcileFailures = 0;
		const after = this.messages.value
			.filter((m) => m.id !== this.pendingAssistantId.value)
			.map((m) => m.id)
			.join();
		this.pageNeedsRefresh ||= hadRun || !!this.activeRun.value || before !== after;
		await this.syncActiveBuild();
		if (this.disposed || this.pageId.value !== pageId || intent !== this.sessionIntentEpoch || this.liveSend)
			return;
		if (this.pageNeedsRefresh && this.isEditingPage.value) {
			const version = this.pageRefreshVersion;
			await this.refreshPage();
			if (this.disposed || this.pageId.value !== pageId || intent !== this.sessionIntentEpoch) return;
			this.pageNeedsRefresh = version !== this.pageRefreshVersion;
			if (this.generationId) this.flushStreamRender();
		}
		if (!this.generationId && !this.activeRun.value) this.endCanvasBuild();
		this.replayHeldEvents();
		await this.replayJournal();
	}

	private async replayJournal() {
		const run = this.activeRun.value;
		if (!run) return;
		const intent = this.sessionIntentEpoch;
		let cursor = this.events.cursor(run.run_id);
		for (let page = 0; page < 10; page++) {
			const result = await createResource({ url: "builder.ai.events.replay" }).submit({
				run_id: run.run_id,
				after_seq: cursor,
			});
			if (this.disposed || intent !== this.sessionIntentEpoch || this.activeRun.value?.run_id !== run.run_id)
				return;
			for (const event of result?.events || []) {
				const handlers: Record<string, (data: any) => unknown> = {
					progress: this.onProgress,
					step: this.onStep,
					stream: this.onStream,
					refetch: this.onRefetch,
					tool_batch: this.onToolBatch,
					complete: this.onComplete,
					error: this.onError,
					clarify: this.onClarify,
				};
				if (handlers[event.type]) await handlers[event.type](event.data);
				else this.events.accept(event.data);
			}
			if (!result?.has_more || result.cursor <= cursor) return;
			cursor = result.cursor;
		}
		this.reconcileAgain = true;
	}

	private async refreshPage() {
		if (this.disposed || this.isUnsavedPage.value) return;
		this.isRefreshingPage.value = true;
		this.builderStore.aiEditEpoch++;
		this.builderStore.aiBuildingCanvas = true;
		try {
			await this.pageStore.setPage(this.pageId.value, false);
		} finally {
			this.isRefreshingPage.value = false;
			if (!this.activeRun.value && !this.generationId) this.endCanvasBuild();
		}
	}

	/** Refresh the session-switcher list (fire-and-forget; the panel renders it). */
	loadSessions = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const pageId = this.pageId.value;
		const rows = await createResource({ url: "builder.ai.api.list_page_ai_sessions" })
			.submit({ page_id: pageId })
			.catch(() => null);
		if (!this.disposed && rows && this.pageId.value === pageId)
			this.sessions.value = rows as Array<{ name: string; title: string | null }>;
	};

	switchSession = async (sessionId: string) => {
		// reselecting the current chat is a no-op only when nothing else is pending
		if (!sessionId || (sessionId === this.sessionId.value && !this.pendingSessionId)) return;
		this.sessionIntentEpoch++;
		this.persistComposer();
		this.resetTransientState();
		this.isSwitchingSession.value = true;
		const intent = this.sessionIntentEpoch;
		try {
			await this.loadSession(sessionId);
		} catch (error) {
			toast.error(getErrorMessage(error, "Could not load this chat"));
		} finally {
			if (intent === this.sessionIntentEpoch) this.isSwitchingSession.value = false;
			this.scheduleReconciliation();
		}
	};

	/** A blank chat. The server only creates its session with the first message. */
	newSession = () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		this.sessionIntentEpoch++;
		this.persistComposer();
		this.invalidateSessionLoads();
		this.resetTransientState();
		this.sessionId.value = "";
		this.messages.value = [];
		this.isSwitchingSession.value = false;
		this.blankSessionSelected = true;
		writeDraft(`selected:${this.pageId.value}`, "");
		this.restoreComposer();
	};

	deleteSession = async () => {
		const sessionId = this.sessionId.value;
		const pageId = this.pageId.value;
		const intent = this.sessionIntentEpoch;
		if (!sessionId || this.isSubmitting.value) return;
		if (!(await confirm("Delete this chat? Its messages are removed; the page itself is untouched."))) return;
		if (this.disposed || intent !== this.sessionIntentEpoch || this.isSubmitting.value) return;
		try {
			await createResource({ url: "builder.ai.api.delete_ai_session" }).submit({ session_id: sessionId });
		} catch (error) {
			toast.error(getErrorMessage(error, "Could not delete this chat"));
			return;
		}
		if (this.disposed || intent !== this.sessionIntentEpoch || this.pageId.value !== pageId) return;
		this.sessionIntentEpoch++;
		this.invalidateSessionLoads();
		writeDraft(this.composerKey(), null);
		this.resetTransientState();
		this.sessionId.value = "";
		this.retryEnvelope.value = null;
		this.blankSessionSelected = false;
		await this.reconcile();
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
		const intent = this.sessionIntentEpoch;
		const reader = new FileReader();
		reader.onload = (e) => {
			if (this.disposed || intent !== this.sessionIntentEpoch) return;
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
		if (!data.session_id) return false;
		return data.session_id !== this.sessionId.value;
	}

	private acceptEvent(data: AIRunEvent, replay: () => void, canvas = false): boolean {
		if (this.disposed || !data.run_id || this.events.finished(data.run_id)) return false;
		if (this.liveSend && !this.activeRun.value) {
			if (this.heldEvents.length < 1000) this.heldEvents.push({ runId: data.run_id, replay });
			return false;
		}
		if (this.isForeignSession(data)) {
			if (data.journal) {
				if (canvas) this.requestReconciliation(true);
				return false;
			}
			if (!canvas) return false;
			if (this.observedRuns.get(data.session_id) !== data.run_id) {
				this.verifyForeignRun(data, replay);
				return false;
			}
		} else if (this.activeRun.value?.run_id !== data.run_id) {
			if (this.heldEvents.length < 1000) this.heldEvents.push({ runId: data.run_id, replay });
			this.requestReconciliation();
			return false;
		}
		const accepted = this.events.accept(data, replay);
		if (!accepted && data.journal && data.seq > this.events.cursor(data.run_id)) this.requestReconciliation();
		return accepted;
	}

	private verifyForeignRun(data: AIRunEvent, replay: () => void) {
		const pending = this.foreignEvents.get(data.session_id);
		if (pending) {
			if (pending.length < 1000) pending.push({ data, replay });
			return;
		}
		const events = [{ data, replay }];
		this.foreignEvents.set(data.session_id, events);
		const pageId = this.pageId.value;
		void createResource({ url: "builder.ai.api.get_ai_session" })
			.submit({
				page_id: pageId,
				session_id: data.session_id,
			})
			.then((session: AISession) => {
				if (this.disposed || this.pageId.value !== pageId) return;
				const run = session.active_run;
				const previous = this.observedRuns.get(data.session_id);
				if (previous && previous !== run?.run_id) this.events.finish(previous);
				if (run) this.observedRuns.set(data.session_id, run.run_id);
				for (const event of events) {
					if (event.data.run_id === run?.run_id) event.replay();
					else this.events.finish(event.data.run_id);
				}
				this.requestReconciliation(true);
			})
			.catch(() => this.requestReconciliation(true))
			.finally(() => {
				if (this.foreignEvents.get(data.session_id) === events) this.foreignEvents.delete(data.session_id);
			});
	}

	private replayHeldEvents() {
		this.heldEvents.splice(0).forEach(({ runId, replay }) => {
			if (runId === this.activeRun.value?.run_id) replay();
		});
		if (!this.cancelOnceKnown || !this.activeRun.value) return;
		this.cancelOnceKnown = false;
		void this.cancel();
	}

	/** The turn's headline status ("Thinking with Claude Sonnet 5"), for the panel
	 * header only. What the turn is DOING belongs to the timeline now — writing it
	 * into the bubble as well just says the same thing twice. */
	onProgress = (data: AIRunEvent & { message?: string }) => {
		if (!this.acceptEvent(data, () => this.onProgress(data))) return;
		this.isSubmitting.value = true;
		this.progressMessage.value = data.message || this.progressMessage.value;
	};

	/** One timeline entry, upserted by id: the model thinking, a tool running, or the
	 * narration it wrote before moving on. A "text" step is also the signal that the
	 * round is over — whatever has been streaming becomes part of the timeline and the
	 * live answer resets for the next round. */
	onStep = (data: AITurnStep & AIRunEvent) => {
		if (!this.acceptEvent(data, () => this.onStep(data)) || typeof data.id !== "number") return;
		if ((this.stepSequences.get(data.id) ?? -1) > data.seq) return;
		this.stepSequences.set(data.id, data.seq);
		this.isSubmitting.value = true;
		const { session_id, page_id, run_id, seq, ...step } = data as Record<string, any>;
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

	onStream = (
		data: AIRunEvent & {
			generation_id?: string;
			chunk?: string;
			kind?: string;
			offset?: number;
			replace?: boolean;
		},
	) => {
		if (!data.chunk && !data.replace) return;
		if (!this.acceptEvent(data, () => this.onStream(data), data.kind === "page_yaml")) return;
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
	onRefetch = async (data: AIRunEvent & { resources?: string[] }) => {
		if (!this.acceptEvent(data, () => this.onRefetch(data), true)) return;
		const resources = data.resources || [];
		if (resources.includes("variables")) {
			builderTokens.reload();
		}
		if (resources.includes("page_data") || resources.includes("page")) {
			const pageId = this.pageId.value;
			const pageLoadToken = this.pageStore.pageLoadToken;
			const page = await this.pageStore.fetchActivePage(pageId).catch(() => null);
			// another page may have opened meanwhile, and its canvas autosaves to activePage
			if (
				this.disposed ||
				this.events.finished(data.run_id) ||
				pageLoadToken !== this.pageStore.pageLoadToken ||
				this.pageStore.selectedPage !== pageId
			)
				return;
			if (page) {
				this.pageStore.activePage = page;
				if (resources.includes("page_data")) await this.pageStore.setPageData(page);
			}
		}
	};

	onToolBatch = (
		data: AIRunEvent & {
			operations?: Array<{ tool_name: string; args: Record<string, any> }>;
		},
	) => {
		if (!this.acceptEvent(data, () => this.onToolBatch(data), true)) return;
		this.clearStreamRenderTimer();
		const operations = data.operations;
		if (!operations?.length) return;
		this.buildEpoch++;
		if (this.isRefreshingPage.value) {
			this.pageStore.pageLoadToken++;
			this.requestReconciliation(true);
		}
		if (
			this.generationRunId === data.run_id &&
			operations.some((op) => ["generate_page", "set_page_blocks"].includes(op.tool_name))
		) {
			this.resetGeneration();
		}
		const ownTurn = !this.isForeignSession(data);

		this.applyServerEdit(() => {
			for (const op of operations) {
				// before apply: a removed block can't be named afterwards
				if (ownTurn) this.dispatcher.trackAffectedItem(op.tool_name, op.args);
				try {
					this.dispatcher.applyToolOperation(op.tool_name, op.args);
				} catch (e) {
					console.warn(`[AI agent] tool "${op.tool_name}" failed:`, e);
				}
			}
		});
		const followId = this.followTargetIn(operations);
		if (followId) nextTick(() => this.pageCanvas.value?.followBlock(followId));
		// Don't overwrite the bubble with a static "Applying N changes…" — the loop emits
		// a per-round progress note (the model's words, or a "Updated N blocks" summary)
		// right after each batch, which is what the user actually sees update.
		this.scrollToBottom();
	};

	/** Mirror edits the server already saved. Autosave stands down so the client
	 * copy can't land as the last write, and the batch is one undo step: Vue's deep
	 * watchers fire after `apply` returns, so both resume on the next tick (which is
	 * also why history.batch(), resuming synchronously, would leave an empty step). */
	private applyServerEdit(apply: () => void) {
		this.builderStore.aiEditEpoch++;
		const pauseId = this.pageCanvas.value?.history?.pause();
		const wasQuiet = this.builderStore.aiBuildingCanvas;
		this.builderStore.aiBuildingCanvas = true;
		try {
			apply();
		} finally {
			nextTick(() => {
				// a whole-tree op rebuilt the history, and the new one ignores this id
				if (pauseId) this.pageCanvas.value?.history?.resume(pauseId, true);
				if (!this.disposed && !wasQuiet && !this.activeRun.value && !this.generationId)
					this.builderStore.aiBuildingCanvas = false;
			});
		}
	}

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

	private finishRun(data: AIRunEvent, content: string, metadata: Record<string, any>) {
		this.events.finish(data.run_id);
		this.buildEpoch++;
		if (this.generationRunId === data.run_id) this.resetGeneration();
		this.pageNeedsRefresh = true;
		if (!this.isForeignSession(data)) {
			const affected = {
				affectedBlocks: [...this.dispatcher.pendingAffectedBlocks.value],
				affectedScripts: [...this.dispatcher.pendingAffectedScripts.value],
			};
			this.affectedByRun.set(data.run_id, affected);
			if (affected.affectedBlocks.length || affected.affectedScripts.length) {
				void createResource({ url: "builder.ai.api.update_session_message_metadata" })
					.submit({ session_id: data.session_id, run_id: data.run_id, metadata: affected })
					.catch(() => null);
			}
			this.invalidateSessionLoads();
			this.replacePendingAssistant(content, metadata);
			this.activeRun.value = null;
			this.isSubmitting.value = false;
			this.isCancelling.value = false;
			this.pendingAssistantId.value = null;
			this.progressMessage.value = "";
			this.summaryContent.value = "";
			this.liveSteps.value = [];
			this.stepSequences.clear();
			this.dispatcher.reset();
		}
		this.requestReconciliation(true);
	}

	onComplete = async (data: AIRunEvent & { message?: string }) => {
		if (!this.acceptEvent(data, () => this.onComplete(data), true)) return;
		const metadata: Record<string, any> = { status: "complete" };
		if (!this.isForeignSession(data)) {
			metadata.affectedBlocks = [...this.dispatcher.pendingAffectedBlocks.value];
			metadata.affectedScripts = [...this.dispatcher.pendingAffectedScripts.value];
		}
		this.finishRun(data, data.message || "Done", metadata);
	};

	onError = async (data: AIRunEvent & { message?: string }) => {
		if (!this.acceptEvent(data, () => this.onError(data), true)) return;
		this.finishRun(data, data.message || "Request failed", { status: "error" });
	};

	onClarify = async (
		data: AIRunEvent & {
			question?: string;
			ui?: Array<Record<string, any>>;
			card_id?: string;
			pending_action?: { kind: string; payload: Record<string, any> };
		},
	) => {
		if (!this.acceptEvent(data, () => this.onClarify(data), true)) return;
		const metadata = data.pending_action
			? { status: "pending_action", ...data.pending_action }
			: { status: "ui", text: data.question || "", ui: data.ui || [], cardId: data.card_id };
		this.finishRun(data, data.question || "…", metadata);
	};

	// --- user actions -----------------------------------------------------

	/** Submit a reply composed by an agent UI card (option tap, action button,
	 * collected form values) as the user's next ordinary message. `display` is
	 * the compact line the chat shows instead of the full relay — the model
	 * still receives the full reply. */
	selectOption = (option: string, display?: string, answer?: CardSubmission) => {
		if (this.isSubmitting.value || this.isSwitchingSession.value || this.isReverting.value) return;
		this.prompt.value = option;
		this.pendingDisplayText = display?.trim() || null;
		this.pendingCardAnswer = answer || null;
		this.submitPrompt();
	};

	/** Apply or skip a sensitive action the agent proposed (create doctype, seed data,
	 * global settings, publish). The privileged write happens server-side in the endpoint;
	 * we reload the session so the message's status flips out of "pending_action". */
	confirmPendingAction = async (message: ChatMessage, decision: "apply" | "skip") => {
		const sessionId = this.sessionId.value;
		const pageId = this.pageId.value;
		const intent = this.sessionIntentEpoch;
		if (!sessionId || this.isSubmitting.value || this.isSwitchingSession.value) return;
		try {
			const res = await createResource({
				url: "builder.ai.api.confirm_pending_settings",
				method: "POST",
			}).submit({ message_id: message.id, decision });
			if (
				this.disposed ||
				intent !== this.sessionIntentEpoch ||
				this.sessionId.value !== sessionId ||
				this.pageId.value !== pageId
			)
				return;
			if (decision === "apply") toast.success(res?.message || "Applied");
			// The continuation can already have finished before this response arrives.
			// Only durable active_run state may create its pending assistant.
			this.requestReconciliation(true);
			await this.reconcilePromise;
		} catch (error) {
			toast.error(getErrorMessage(error, "Could not apply the change"));
		}
	};

	cancel = async () => {
		if (this.liveSend && !this.activeRun.value) {
			this.cancelOnceKnown = true;
			this.progressMessage.value = "Cancelling…";
			return;
		}
		const run = this.activeRun.value;
		const intent = this.sessionIntentEpoch;
		if (!run || !this.isSubmitting.value || this.isCancelling.value) return;
		this.isCancelling.value = true;
		this.progressMessage.value = "Cancelling…";
		try {
			await createResource({ url: "builder.ai.api.cancel" }).submit({
				session_id: run.session_id,
				run_id: run.run_id,
			});
			if (this.disposed || intent !== this.sessionIntentEpoch || this.activeRun.value?.run_id !== run.run_id)
				return;
			// Queued cancellation is durable without a terminal socket event. Even
			// "not_running" needs hydration: another tab may have started a new run.
			this.requestReconciliation(true);
			await this.reconcilePromise;
		} catch (error) {
			if (intent !== this.sessionIntentEpoch || this.activeRun.value?.run_id !== run.run_id) return;
			this.isCancelling.value = false;
			this.progressMessage.value = "";
			toast.error(getErrorMessage(error, "Could not stop the run. Try again."));
			this.requestReconciliation();
		}
	};

	private sendEnvelope(): SendEnvelope {
		const content = {
			pageId: this.pageId.value,
			sessionId: this.sessionId.value,
			model: this.selectedModel.value,
			prompt: this.prompt.value.trim(),
			blocks: this.attachedBlocks.value.map((block) => ({ ...block })),
			imageData: this.imageData.value,
			imagePreviewUrl: this.imagePreviewUrl.value,
			imageFileName: this.imageFileName.value,
			displayText: this.pendingDisplayText,
			cardAnswer: this.pendingCardAnswer,
			canvasTheme: this.builderStore.canvasDarkMode ? "dark" : "light",
		};
		const previous = this.retryEnvelope.value;
		if (previous) {
			const { requestId, attempted, ...original } = previous;
			if (JSON.stringify(original) === JSON.stringify(content)) return previous;
		}
		return { ...content, requestId: crypto.randomUUID(), attempted: false };
	}

	submitPrompt = async () => {
		if (this.disposed || !this.canSubmit.value || this.isUnsavedPage.value) return;
		this.sessionIntentEpoch++;
		this.invalidateSessionLoads();
		const envelope = this.sendEnvelope();
		this.retryEnvelope.value = envelope;
		const turn = ++this.turnCount;
		this.liveSend = turn;
		const stillOwned = () =>
			!this.disposed && this.pageId.value === envelope.pageId && this.liveSend === turn;
		this.prompt.value = "";
		this.attachedBlocks.value = [];
		this.clearImage();
		this.pendingDisplayText = null;
		this.pendingCardAnswer = null;

		const userMessage = buildLocalMessage("user", envelope.prompt, {
			selectedBlockContext: envelope.blocks,
			attachedImageUrl: envelope.imagePreviewUrl,
			displayText: envelope.displayText,
			cardAnswer: envelope.cardAnswer,
		});
		const assistantMessage = buildLocalMessage("assistant", "", { status: "running" });
		this.messages.value.push(userMessage, assistantMessage);
		this.pendingAssistantId.value = assistantMessage.id;
		this.scrollToBottom();
		this.summaryContent.value = "";
		this.liveSteps.value = [];
		this.stepSequences.clear();
		this.dispatcher.reset();
		this.activeRun.value = null;
		this.isSubmitting.value = true;
		let accepted = false;

		try {
			if (this.pageNeedsRefresh) {
				await this.refreshPage();
				if (!stillOwned()) return;
				this.pageNeedsRefresh = false;
			}
			// An ambiguous retry may already be editing the server draft. Saving the
			// stale local canvas again would overwrite that accepted work.
			if (!envelope.attempted) await this.pageStore.savePage();
			if (!stillOwned()) return;
			envelope.attempted = true;
			this.persistComposer();
			const response = await createResource({ url: "builder.ai.api.run" }).submit({
				request_id: envelope.requestId,
				prompt: envelope.prompt,
				page_id: envelope.pageId,
				model: envelope.model,
				session_id: envelope.sessionId,
				selected_block_ids: envelope.blocks.map((block) => block.id),
				selected_block_context: envelope.blocks,
				...(envelope.imageData ? { image_data: envelope.imageData } : {}),
				...(envelope.displayText ? { display_text: envelope.displayText } : {}),
				...(envelope.cardAnswer ? { card_answer: envelope.cardAnswer } : {}),
				canvas_theme: envelope.canvasTheme,
			});
			if (!stillOwned()) return;
			if (response?.status !== "accepted" || !response.run_id || !response.session_id) {
				throw new Error(response?.message || "Could not send the message");
			}
			accepted = true;
			writeDraft(this.composerKey(), null);
			this.retryEnvelope.value = null;
			this.sessionId.value = response.session_id;
			this.blankSessionSelected = false;
			writeDraft(`selected:${envelope.pageId}`, response.session_id);
			this.activeRun.value = {
				run_id: response.run_id,
				session_id: response.session_id,
				status: "queued",
				model: envelope.model,
				user_message_id: userMessage.id,
			};
			this.observedRuns.set(response.session_id, response.run_id);
			this.persistComposer();
			this.loadSessions();
		} catch (error) {
			if (stillOwned()) this.failSend([userMessage.id, assistantMessage.id], envelope, error);
		} finally {
			if (this.liveSend === turn) {
				this.liveSend = 0;
				if (accepted) {
					this.replayHeldEvents();
					this.requestReconciliation();
				} else {
					this.heldEvents = [];
					this.cancelOnceKnown = false;
					this.scheduleReconciliation();
				}
			}
		}
	};

	private failSend(messageIds: string[], envelope: SendEnvelope, error: unknown) {
		this.messages.value = this.messages.value.filter((m) => !messageIds.includes(m.id));
		this.pendingAssistantId.value = null;
		this.isSubmitting.value = false;
		this.isCancelling.value = false;
		this.prompt.value = envelope.prompt;
		this.attachedBlocks.value = envelope.blocks.map((block) => ({ ...block }));
		this.imageData.value = envelope.imageData;
		this.imagePreviewUrl.value = envelope.imagePreviewUrl;
		this.imageFileName.value = envelope.imageFileName;
		this.pendingDisplayText = envelope.displayText;
		this.pendingCardAnswer = envelope.cardAnswer || null;
		this.persistComposer();
		toast.error(getErrorMessage(error, "Could not send the message. Retry to check the same request."));
	}

	revertTurn = async (message: ChatMessage) => {
		const sessionId = this.sessionId.value;
		const pageId = this.pageId.value;
		const intent = this.sessionIntentEpoch;
		if (
			!message.metadata?.revertSnapshot ||
			!sessionId ||
			this.isSubmitting.value ||
			!this.isEditingPage.value ||
			this.isReverting.value
		)
			return;
		const confirmed = await confirm(
			"Revert this AI edit? The page's blocks, page data and scripts return to before this turn, and this turn and all later messages are removed. Shared scripts may affect other pages.",
		);
		if (!confirmed || this.disposed || intent !== this.sessionIntentEpoch || this.isSubmitting.value) return;
		this.isReverting.value = true;
		this.invalidateSessionLoads();
		try {
			const result = await createResource({ url: "builder.ai.api.revert_to_message" }).submit({
				session_id: sessionId,
				message_id: message.id,
			});
			if (this.disposed || this.pageId.value !== pageId || intent !== this.sessionIntentEpoch) return;
			this.hydrateSession({ session_id: sessionId, messages: result.messages, active_run: null });
			this.resetGeneration();
			await this.refreshPage();
		} catch (error) {
			toast.error(getErrorMessage(error, "Could not revert this edit"));
			throw error;
		} finally {
			this.isReverting.value = false;
		}
	};

	selectBlockById = (blockId: string) => {
		const block = this.pageCanvas.value?.findBlock(blockId);
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
				if (!this.disposed) this.availableModels.value = data;
			},
		});
	}

	async mount() {
		this.mounted = true;
		if (this.pageId.value)
			attachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
		this.builderStore.realtime.on("connect", this.onReconnect);
		window.addEventListener("online", this.onReconnect);
		document.addEventListener("visibilitychange", this.onVisibility);
		this.loadModels();
		await this.reconcile();
	}

	unmount() {
		this.persistComposer();
		this.disposed = true;
		this.mounted = false;
		this.sessionIntentEpoch++;
		this.invalidateSessionLoads();
		this.liveSend = 0;
		this.heldEvents = [];
		this.foreignEvents.clear();
		this.stopWatchers.splice(0).forEach((stop) => stop());
		clearTimeout(this.reconcileTimer);
		this.resetGeneration();
		this.endCanvasBuild();
		if (this.scrollFrame) cancelAnimationFrame(this.scrollFrame);
		if (this.isRefreshingPage.value) this.pageStore.pageLoadToken++;
		if (this.pageId.value)
			detachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
		this.builderStore.realtime.off("connect", this.onReconnect);
		window.removeEventListener("online", this.onReconnect);
		document.removeEventListener("visibilitychange", this.onVisibility);
	}
}
