import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import type { BuilderClientScript } from "@/types/Builder/BuilderClientScript";
import { getBlockInstance, getBlockObject } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { createResource } from "frappe-ui";
// @ts-ignore
import yaml from "js-yaml";
import { computed, nextTick, ref, watch } from "vue";
import { useRoute } from "vue-router";

export interface AIModel {
	name: string;
	label: string;
	vision?: boolean;
}

export interface AIProvider {
	provider: string;
	models: AIModel[];
}

export interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
	message_type?: string;
	task_type?: string | null;
	block_id?: string | null;
	created_at?: string;
	metadata?: Record<string, any>;
}

function buildLocalMessage(role: "user" | "assistant", content: string, metadata: Record<string, any> = {}) {
	return {
		id: `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
		role,
		content,
		created_at: new Date().toISOString(),
		metadata,
	} as ChatMessage;
}

function getValidPartialYAML(yamlStr: string): any {
	let cleaned = yamlStr.trim();
	if (cleaned.startsWith("```")) {
		const lines = cleaned.split("\n");
		lines.shift();
		if (lines.at(-1)?.startsWith("```")) lines.pop();
		cleaned = lines.join("\n");
	}
	try {
		return yaml.load(cleaned);
	} catch {
		const lines = cleaned.split("\n");
		for (let i = lines.length - 1; i > 0; i--) {
			try {
				const parsed = yaml.load(lines.slice(0, i).join("\n"));
				if (parsed) return parsed;
			} catch {}
		}
	}
	return null;
}

function convertYAMLtoBlock(yamlBlock: Record<string, any>): BlockOptions {
	if (!yamlBlock || typeof yamlBlock !== "object" || Array.isArray(yamlBlock)) return yamlBlock;
	const ensureObject = (value: any) =>
		value && typeof value === "object" && !Array.isArray(value) ? value : {};
	const ensureArray = (value: any) => (Array.isArray(value) ? value : []);
	const block: BlockOptions = {
		element: yamlBlock.el || "div",
		blockName: yamlBlock.name || "",
		baseStyles: ensureObject(yamlBlock.style),
		attributes: ensureObject(yamlBlock.attrs),
		mobileStyles: ensureObject(yamlBlock.m_style),
		tabletStyles: ensureObject(yamlBlock.t_style),
		classes: ensureArray(yamlBlock.classes),
	};
	if (yamlBlock.id) block.blockId = yamlBlock.id;
	if (yamlBlock.text) block.innerText = yamlBlock.text;
	block.children = Array.isArray(yamlBlock.c) ? yamlBlock.c.map(convertYAMLtoBlock) : [];
	return block;
}

function parseBlock(raw: string): BlockOptions | null {
	const parsed = getValidPartialYAML(raw);
	if (!parsed) return null;
	const block = Array.isArray(parsed) ? parsed[0] : parsed;
	return block && typeof block === "object" && block.el ? convertYAMLtoBlock(block) : null;
}

function replaceBlockInTree(root: Block, targetId: string, replacement: BlockOptions): boolean {
	if (!root || !replacement) return false;
	if (root.blockId === targetId) {
		root.element = replacement.element || root.element;
		root.baseStyles = replacement.baseStyles || root.baseStyles;
		root.mobileStyles = replacement.mobileStyles || root.mobileStyles;
		root.tabletStyles = replacement.tabletStyles || root.tabletStyles;
		root.classes = replacement.classes || root.classes;
		if (replacement.attributes) root.attributes = { ...root.attributes, ...replacement.attributes };
		if (replacement.innerText !== undefined) root.innerText = replacement.innerText;
		if (replacement.innerHTML !== undefined) root.innerHTML = replacement.innerHTML;
		if (replacement.children) {
			root.children.splice(
				0,
				root.children.length,
				...replacement.children.map((child) => getBlockInstance(child as BlockOptions)),
			);
		}
		return true;
	}
	return root.children?.some((child: Block) => replaceBlockInTree(child, targetId, replacement)) || false;
}

export class AIChatController {
	private readonly builderStore = useBuilderStore();
	private readonly canvasStore = useCanvasStore();
	private readonly pageStore = usePageStore();
	private readonly route = useRoute();

	readonly prompt = ref("");
	readonly progressMessage = ref("");
	readonly isSubmitting = ref(false);
	readonly scope = ref<"page" | "selection">("page");
	readonly messageContainer = ref<HTMLElement | null>(null);

	readonly sessionId = ref("");
	readonly messages = ref<ChatMessage[]>([]);
	readonly availableModels = ref<AIProvider[]>([]);
	readonly selectedModel = useLocalStorage("ai-selected-model", "");

	private readonly streamingContent = ref("");
	private readonly remoteTaskType = ref<string | null>(null);
	private readonly remoteBlockId = ref<string | null>(null);
	private readonly pendingAssistantId = ref<string | null>(null);
	private readonly pendingScriptOps = ref<Promise<string | null>[]>([]);

	readonly pageId = computed(() => this.route.params.pageId as string);
	readonly isUnsavedPage = computed(() => !this.pageId.value || this.pageId.value === "new");
	readonly currentProviderModels = computed(() => {
		const found = this.availableModels.value.find((p) => p.provider === "openrouter");
		return found?.models || [];
	});
	readonly selectedBlock = computed<Block | null>(() => {
		return (this.canvasStore.editableBlock ||
			this.canvasStore.activeCanvas?.selectedBlocks?.[0] ||
			null) as Block | null;
	});
	readonly rootBlock = computed<Block | null>(() => {
		return (this.pageStore.pageBlocks[0] || null) as Block | null;
	});
	readonly modelLabel = computed(() => {
		return (
			this.currentProviderModels.value.find((m) => m.name === this.selectedModel.value)?.label ||
			"Select model"
		);
	});
	readonly scopeOptions = computed(() => [
		{ label: "Page", value: "page" },
		{ label: "Selection", value: "selection", disabled: !this.selectedBlock.value },
	]);
	readonly canSubmit = computed(
		() => !!this.prompt.value.trim() && !this.isSubmitting.value && !!this.selectedModel.value,
	);

	constructor() {
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

		watch(this.selectedBlock, (block) => {
			if (!block && this.scope.value === "selection") this.scope.value = "page";
		});

		watch(
			() => [this.messages.value.length, this.progressMessage.value],
			async () => {
				await nextTick();
				this.messageContainer.value?.scrollTo({ top: this.messageContainer.value.scrollHeight });
			},
		);

		watch(this.pageId, async (newPageId, oldPageId) => {
			if (oldPageId) this.detachListeners(oldPageId);
			if (!newPageId) return;
			this.attachListeners(newPageId);
			this.resetTransientState();
			if (newPageId === "new") {
				this.messages.value = [];
				this.sessionId.value = "";
				return;
			}
			await this.loadSession();
		});
	}

	resetTransientState() {
		this.progressMessage.value = "";
		this.streamingContent.value = "";
		this.remoteTaskType.value = null;
		this.remoteBlockId.value = null;
		this.pendingAssistantId.value = null;
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

	messageLabel(message: ChatMessage) {
		const scopeLabel = message.metadata?.scope === "selection" ? "selection" : "page";
		if (message.role === "user") return scopeLabel;
		return message.metadata?.status || message.task_type || "assistant";
	}

	async loadSession() {
		if (!this.pageId.value || !this.builderStore.isAIEnabled || this.isUnsavedPage.value) return;
		const result = await createResource({
			url: "builder.ai.ai_page_generator.get_ai_session",
			makeParams: () => ({ page_id: this.pageId.value, model: this.selectedModel.value }),
		}).submit();
		const session = result as { session_id: string; messages: ChatMessage[] };
		this.sessionId.value = session.session_id;
		this.messages.value = (session.messages || []).map((m) => ({
			...m,
			role: m.role === "user" ? "user" : ("assistant" as const),
		}));
	}

	clearSession = async () => {
		if (!this.pageId.value || this.isUnsavedPage.value) return;
		const result = await createResource({
			url: "builder.ai.ai_page_generator.clear_ai_session",
			makeParams: () => ({ page_id: this.pageId.value }),
		}).submit();
		const session = result as { session_id: string; messages: ChatMessage[] };
		this.sessionId.value = session.session_id;
		this.messages.value = session.messages || [];
		this.resetTransientState();
	};

	private applyPageStream() {
		const block = parseBlock(this.streamingContent.value);
		if (!block) return;
		try {
			this.pageStore.pageBlocks = [getBlockInstance(block)];
			this.canvasStore.activeCanvas?.setRootBlock(this.pageStore.pageBlocks[0] as Block, false);
		} catch {}
	}

	private applyModifyStream() {
		const block = parseBlock(this.streamingContent.value);
		const targetId = this.remoteBlockId.value || this.selectedBlock.value?.blockId;
		if (!block || !targetId || !this.rootBlock.value) return;
		try {
			replaceBlockInTree(this.rootBlock.value, targetId, block);
		} catch {}
	}

	onProgress = (data: { message?: string; task_type?: string; block_id?: string }) => {
		this.isSubmitting.value = true;
		this.progressMessage.value = data.message || this.progressMessage.value;
		if (data.task_type) this.remoteTaskType.value = data.task_type;
		if (data.block_id) this.remoteBlockId.value = data.block_id;
		this.replacePendingAssistant(this.progressMessage.value || "Working...", { status: "running" });
	};

	onStream = (data: { chunk?: string; task_type?: string; block_id?: string }) => {
		if (!data.chunk) return;
		this.isSubmitting.value = true;
		this.streamingContent.value += data.chunk;
		if (data.task_type) this.remoteTaskType.value = data.task_type;
		if (data.block_id) this.remoteBlockId.value = data.block_id;
		if (this.remoteTaskType.value || this.scope.value === "selection") {
			this.applyModifyStream();
		} else {
			this.applyPageStream();
		}
	};

	onComplete = async (data: { message?: string }) => {
		this.isSubmitting.value = false;
		this.progressMessage.value = data.message || "Applied update";

		let undoScripts: string[] = [];
		if (this.pendingScriptOps.value.length) {
			const names = await Promise.all(this.pendingScriptOps.value);
			undoScripts = names.filter((n): n is string => !!n);
			this.pendingScriptOps.value = [];
		}

		const meta: Record<string, any> = { status: "complete" };
		if (undoScripts.length) meta.undoScripts = undoScripts;
		this.replacePendingAssistant(this.progressMessage.value, meta);
		this.pageStore.savePage();
		this.prompt.value = "";
		this.streamingContent.value = "";
		this.remoteTaskType.value = null;
		this.remoteBlockId.value = null;
		await this.loadSession();
		window.setTimeout(() => {
			this.progressMessage.value = "";
			this.pendingAssistantId.value = null;
		}, 1200);
	};

	onError = async (data: { message?: string }) => {
		this.isSubmitting.value = false;
		this.progressMessage.value = "";
		this.replacePendingAssistant(data.message || "Request failed", { status: "error" });
		this.streamingContent.value = "";
		this.remoteTaskType.value = null;
		this.remoteBlockId.value = null;
		await this.loadSession();
		this.pendingAssistantId.value = null;
	};

	onAgentToolBatch = (data: { operations?: Array<{ tool_name: string; args: Record<string, any> }> }) => {
		if (!data.operations?.length) return;
		for (const op of data.operations) {
			try {
				this.applyToolOperation(op.tool_name, op.args);
			} catch (e) {
				console.warn(`[AI agent] tool "${op.tool_name}" failed:`, e);
			}
		}
		const n = data.operations.length;
		this.replacePendingAssistant(`Applied ${n} change${n !== 1 ? "s" : ""}…`, { status: "running" });
	};

	findBlockInTree(blockId: string, root?: Block | null): Block | null {
		const searchRoot = root !== undefined ? root : this.rootBlock.value;
		if (!searchRoot) return null;
		if (searchRoot.blockId === blockId) return searchRoot;
		for (const child of searchRoot.children || []) {
			const found = this.findBlockInTree(blockId, child as Block);
			if (found) return found;
		}
		return null;
	}

	applyToolOperation(toolName: string, args: Record<string, any>) {
		switch (toolName) {
			case "update_block": {
				const block = this.findBlockInTree(args.block_id);
				if (!block) return;
				if (args.base_styles) {
					Object.entries(args.base_styles).forEach(([key, value]) =>
						block.setBaseStyle(key as any, value as StyleValue),
					);
				}
				if (args.mobile_styles) {
					Object.entries(args.mobile_styles).forEach(([key, value]) => {
						block.mobileStyles[key] = value as StyleValue;
					});
				}
				if (args.tablet_styles) {
					Object.entries(args.tablet_styles).forEach(([key, value]) => {
						block.tabletStyles[key] = value as StyleValue;
					});
				}
				if (args.attributes) {
					Object.entries(args.attributes).forEach(([key, value]) =>
						block.setAttribute(key, value as string | undefined),
					);
				}
				if (args.inner_text !== undefined) block.setInnerHTML(args.inner_text);
				if (args.inner_html !== undefined) block.setInnerHTML(args.inner_html);
				if (args.element !== undefined) block.element = args.element;
				if (args.classes !== undefined) block.classes = args.classes;
				return;
			}
			case "add_block": {
				const parent = this.findBlockInTree(args.parent_block_id);
				if (!parent) return;
				const newBlock = getBlockInstance(convertYAMLtoBlock(args.block as Record<string, any>));
				if (args.after_block_id) {
					const sibling = this.findBlockInTree(args.after_block_id, parent);
					if (sibling) {
						parent.addChildAfter(newBlock, sibling);
						return;
					}
				}
				parent.addChild(newBlock, typeof args.index === "number" ? args.index : null);
				return;
			}
			case "remove_block": {
				const block = this.findBlockInTree(args.block_id);
				if (!block) return;
				block.getParentBlock()?.removeChild(block);
				return;
			}
			case "move_block": {
				const block = this.findBlockInTree(args.block_id);
				const newParent = this.findBlockInTree(args.new_parent_block_id);
				if (!block || !newParent) return;
				block.getParentBlock()?.removeChild(block);
				if (args.after_block_id) {
					const sibling = this.findBlockInTree(args.after_block_id, newParent);
					if (sibling) {
						newParent.addChildAfter(block, sibling);
						return;
					}
				}
				newParent.addChild(block, typeof args.index === "number" ? args.index : null, false);
				return;
			}
			case "set_page_script": {
				const scriptType = (args.script_type as string) || "JavaScript";
				const op = createResource({ url: "frappe.client.insert" })
					.submit({
						doc: { doctype: "Builder Client Script", script_type: scriptType, script: args.script as string },
					})
					.then((res: BuilderClientScript) =>
						createResource({ url: "frappe.client.insert" })
							.submit({
								doc: {
									doctype: "Builder Page Client Script",
									parent: this.pageId.value,
									parenttype: "Builder Page",
									parentfield: "client_scripts",
									builder_script: res.name,
								},
							})
							.then(() => {
								this.pageStore.activePageScripts.push(res);
								return res.name;
							}),
					)
					.catch(() => null);
				this.pendingScriptOps.value.push(op);
				return;
			}
		}
	}

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

	private get listenerMap() {
		return {
			ai_generation_progress: this.onProgress,
			ai_generation_stream: this.onStream,
			ai_generation_complete: this.onComplete,
			ai_generation_error: this.onError,
			ai_modify_progress: this.onProgress,
			ai_modify_stream: this.onStream,
			ai_modify_complete: this.onComplete,
			ai_modify_error: this.onError,
			ai_agent_progress: this.onProgress,
			ai_agent_tool_batch: this.onAgentToolBatch,
			ai_agent_stream: this.onStream,
			ai_agent_complete: this.onComplete,
			ai_agent_error: this.onError,
		};
	}

	private eventName(base: string, targetPageId: string) {
		return targetPageId ? `${base}_${targetPageId}` : base;
	}

	attachListeners(targetPageId: string) {
		Object.entries(this.listenerMap).forEach(([event, handler]) => {
			this.builderStore.realtime.on(this.eventName(event, targetPageId), handler);
		});
	}

	detachListeners(targetPageId: string) {
		Object.entries(this.listenerMap).forEach(([event, handler]) => {
			this.builderStore.realtime.off(this.eventName(event, targetPageId), handler);
		});
	}

	private isGenerateMode() {
		if (this.scope.value === "selection") return false;
		return !this.rootBlock.value || !this.rootBlock.value.children?.length;
	}

	submitPrompt = async () => {
		if (!this.canSubmit.value || !this.pageId.value || this.isUnsavedPage.value) return;
		if (!this.sessionId.value) await this.loadSession();

		const userText = this.prompt.value.trim();
		const userMessage = buildLocalMessage("user", userText, { scope: this.scope.value });
		const assistantMessage = buildLocalMessage("assistant", "Working...", { status: "running" });
		this.messages.value.push(userMessage, assistantMessage);
		this.pendingAssistantId.value = assistantMessage.id;
		this.streamingContent.value = "";
		this.remoteTaskType.value = null;
		this.remoteBlockId.value = null;
		this.isSubmitting.value = true;

		const runGenerate = this.scope.value === "page" && this.isGenerateMode();
		const runAgent = this.scope.value === "page" && !runGenerate;
		const targetBlock = this.scope.value === "selection" ? this.selectedBlock.value : this.rootBlock.value;

		let url: string;
		let extraParams: Record<string, any> = {};
		if (runGenerate) {
			url = "builder.ai.ai_page_generator.generate_page_from_prompt";
		} else if (runAgent) {
			url = "builder.ai.ai_page_generator.run_agent_from_prompt";
			extraParams = { page_context: JSON.stringify(getBlockObject(this.rootBlock.value as Block)) };
		} else {
			url = "builder.ai.ai_page_generator.modify_section_from_prompt";
			extraParams = { block_context: JSON.stringify(getBlockObject(targetBlock as Block)) };
		}

		try {
			const result = await createResource({
				url,
				makeParams: () => ({
					prompt: userText,
					page_id: this.pageId.value,
					model: this.selectedModel.value,
					session_id: this.sessionId.value,
					...extraParams,
				}),
			}).submit();
			const response = result as { session_id?: string };
			if (response.session_id) this.sessionId.value = response.session_id;
		} catch (error) {
			await this.onError({ message: error instanceof Error ? error.message : "Request failed" });
		}
	};

	async mount() {
		if (this.pageId.value) this.attachListeners(this.pageId.value);
		createResource({
			url: "builder.ai.ai_page_generator.get_ai_models",
			auto: true,
			onSuccess: (data: AIProvider[]) => {
				this.availableModels.value = data;
			},
		});
		await this.loadSession();
	}

	unmount() {
		if (this.pageId.value) this.detachListeners(this.pageId.value);
	}
}
