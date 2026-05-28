import type Block from "@/block";
import { type AIChatHandlers, attachAIChatListeners, detachAIChatListeners } from "@/components/ai/realtime";
import { ToolDispatcher } from "@/components/ai/toolDispatch";
import type { AIProvider, ChatMessage } from "@/components/ai/types";
import { buildLocalMessage } from "@/components/ai/yaml";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import type { BuilderClientScript } from "@/types/Builder/BuilderClientScript";
import { getBlockObject } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { createResource } from "frappe-ui";
import { computed, nextTick, ref, watch } from "vue";
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
	readonly messageContainer = ref<HTMLElement | null>(null);

	readonly imageData = ref<string | null>(null);
	readonly imagePreviewUrl = ref<string | null>(null);
	readonly imageFileName = ref("");
	readonly isDragging = ref(false);

	readonly sessionId = ref("");
	readonly messages = ref<ChatMessage[]>([]);
	readonly availableModels = ref<AIProvider[]>([]);
	readonly selectedModel = useLocalStorage("ai-selected-model", "");

	// Set by the panel's style-preset picker; folded into the prompt on submit.
	pendingStylePreset: string | null = null;

	private readonly pageStreamContent = ref(""); // accumulates kind="page_yaml" chunks
	private readonly summaryContent = ref(""); // accumulates summary chunks
	private readonly pendingAssistantId = ref<string | null>(null);
	private submittedForPageId: string | null = null;

	readonly pageId = computed(() => this.route.params.pageId as string);
	readonly isUnsavedPage = computed(() => !this.pageId.value || this.pageId.value === "new");
	readonly currentProviderModels = computed(
		() => this.availableModels.value.find((p) => p.provider === "openrouter")?.models || [],
	);
	readonly selectedBlocks = computed<Block[]>(
		() => (this.canvasStore.activeCanvas?.selectedBlocks || []) as Block[],
	);
	readonly rootBlock = computed<Block | null>(() => (this.pageStore.pageBlocks[0] || null) as Block | null);
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
			if (newPageId === "new") {
				this.messages.value = [];
				this.sessionId.value = "";
				return;
			}
			await this.loadSession();
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
		};
	}

	resetTransientState() {
		this.progressMessage.value = "";
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.pendingAssistantId.value = null;
		this.dispatcher.reset();
		this.isSubmitting.value = false;
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

	async loadSession() {
		if (!this.pageId.value || !this.builderStore.isAIEnabled || this.isUnsavedPage.value) return;
		const result = await createResource({
			url: "builder.ai.api.get_ai_session",
			makeParams: () => ({ page_id: this.pageId.value, model: this.selectedModel.value }),
		}).submit();
		const session = result as { session_id: string; messages: ChatMessage[] };
		this.sessionId.value = session.session_id;
		this.messages.value = (session.messages || []).map(
			(m) => ({ ...m, role: m.role === "user" ? "user" : "assistant" } as ChatMessage),
		);
	}

	clearSession = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const result = await createResource({
			url: "builder.ai.api.clear_ai_session",
			makeParams: () => ({ page_id: this.pageId.value }),
		}).submit();
		const session = result as { session_id: string; messages: ChatMessage[] };
		this.sessionId.value = session.session_id;
		this.messages.value = session.messages || [];
		this.resetTransientState();
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

	onProgress = (data: { message?: string }) => {
		this.isSubmitting.value = true;
		this.progressMessage.value = data.message || this.progressMessage.value;
		this.replacePendingAssistant(this.progressMessage.value || "Working...", { status: "running" });
		this.scrollToBottom();
	};

	onStream = (data: { chunk?: string; kind?: string }) => {
		if (!data.chunk) return;
		this.isSubmitting.value = true;
		if (data.kind === "page_yaml") {
			if (this.submittedForPageId && this.submittedForPageId !== this.pageId.value) return;
			this.pageStreamContent.value += data.chunk;
			try {
				this.dispatcher.applyPageYaml(this.pageStreamContent.value);
			} catch {}
		} else {
			this.summaryContent.value += data.chunk;
			this.replacePendingAssistant(this.summaryContent.value, { status: "running" });
			this.scrollToBottom();
		}
	};

	onToolBatch = (data: { operations?: Array<{ tool_name: string; args: Record<string, any> }> }) => {
		if (!data.operations?.length) return;
		for (const op of data.operations) {
			this.dispatcher.trackAffectedItem(op.tool_name, op.args); // track before apply (remove_block)
			try {
				this.dispatcher.applyToolOperation(op.tool_name, op.args);
			} catch (e) {
				console.warn(`[AI agent] tool "${op.tool_name}" failed:`, e);
			}
		}
		const n = data.operations.length;
		this.replacePendingAssistant(`Applying ${n} change${n !== 1 ? "s" : ""}…`, { status: "running" });
		this.scrollToBottom();
	};

	onComplete = async (data: { message?: string }) => {
		if (this.submittedForPageId && this.submittedForPageId !== this.pageId.value) {
			this.submittedForPageId = null;
			return;
		}
		this.submittedForPageId = null;
		this.isSubmitting.value = false;
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
		if (localMeta.affectedBlocks?.length || localMeta.affectedScripts?.length || localMeta.undoScripts?.length) {
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

	onError = async (data: { message?: string }) => {
		this.isSubmitting.value = false;
		this.progressMessage.value = "";
		this.replacePendingAssistant(data.message || "Request failed", { status: "error" });
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		await this.loadSession();
		this.pendingAssistantId.value = null;
	};

	onClarify = async (data: {
		question?: string;
		options?: string[];
		previews?: Array<{ colors: string[] }> | null;
		ready?: boolean;
		plan_summary?: boolean;
		headline?: string;
		sections?: string[];
		palette?: string;
	}) => {
		this.isSubmitting.value = false;
		this.progressMessage.value = "";
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";

		if (data.plan_summary) {
			this.replacePendingAssistant(data.headline || "Here's my plan", {
				status: "plan_summary",
				headline: data.headline || "",
				sections: data.sections || [],
				palette: data.palette || "",
			});
		} else {
			this.replacePendingAssistant(data.question || "Could you clarify?", {
				status: "clarification",
				options: data.options || [],
				previews: data.previews ?? null,
				ready: data.ready ?? false,
			});
		}
		this.pendingAssistantId.value = null;
		// Backend persists+commits clarify messages before emitting, so this is race-free.
		await this.loadSession();
		this.scrollToBottom();
	};

	// --- user actions -----------------------------------------------------

	selectOption = (option: string) => {
		this.prompt.value = option;
		this.submitPrompt();
	};

	approvePlan = () => {
		this.prompt.value = "Yes, that plan looks good — go ahead and build the page.";
		this.submitPrompt();
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

		const contextMeta: Record<string, any> = {};
		if (selectedBlockContext.length) contextMeta.selectedBlockContext = selectedBlockContext;
		if (attachedImageUrl) contextMeta.attachedImageUrl = attachedImageUrl;

		const userMessage = buildLocalMessage("user", userText, contextMeta);
		const assistantMessage = buildLocalMessage("assistant", "Thinking...", { status: "running" });
		this.messages.value.push(userMessage, assistantMessage);
		this.pendingAssistantId.value = assistantMessage.id;
		this.scrollToBottom();
		this.pageStreamContent.value = "";
		this.summaryContent.value = "";
		this.dispatcher.reset();
		this.isSubmitting.value = true;

		const pageContext = this.rootBlock.value
			? JSON.stringify(getBlockObject(this.rootBlock.value as Block))
			: "[]";

		try {
			const result = await createResource({
				url: "builder.ai.api.run",
				makeParams: () => ({
					prompt: userText,
					page_id: this.pageId.value,
					model: this.selectedModel.value,
					session_id: this.sessionId.value,
					page_context: pageContext,
					...(selectedIds.length ? { selected_block_ids: selectedIds } : {}),
					...(selectedBlockContext.length ? { selected_block_context: selectedBlockContext } : {}),
					...(attachedImageData ? { image_data: attachedImageData } : {}),
				}),
			}).submit();
			const response = result as { session_id?: string };
			if (response.session_id) this.sessionId.value = response.session_id;
		} catch (error) {
			await this.onError({ message: error instanceof Error ? error.message : "Request failed" });
		}
	};

	undoAgentScript = async (message: ChatMessage) => {
		const scriptNames: string[] = message.metadata?.undoScripts || [];
		await Promise.all(
			scriptNames.map((name) =>
				createResource({ url: "frappe.client.delete" }).submit({ doctype: "Builder Client Script", name }),
			),
		);
		this.pageStore.activePageScripts = this.pageStore.activePageScripts.filter(
			(s: BuilderClientScript) => !scriptNames.includes(s.name),
		);
		const idx = this.messages.value.findIndex((m) => m.id === message.id);
		if (idx !== -1) {
			this.messages.value[idx] = {
				...this.messages.value[idx],
				metadata: { ...this.messages.value[idx].metadata, undoScripts: [] },
			};
		}
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
		if (this.pageId.value) attachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
		createResource({
			url: "builder.ai.api.get_ai_models",
			auto: true,
			onSuccess: (data: AIProvider[]) => {
				this.availableModels.value = data;
			},
		});
		await this.loadSession();
	}

	unmount() {
		if (this.pageId.value) detachAIChatListeners(this.builderStore.realtime, this.pageId.value, this.handlers);
	}
}
