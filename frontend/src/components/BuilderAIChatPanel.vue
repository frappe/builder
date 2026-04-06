<template>
	<div class="flex h-full min-h-full flex-col bg-surface-white">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-3">
			<div>
				<div class="text-sm font-medium text-ink-gray-9">AI Chat</div>
				<div class="text-xs text-ink-gray-5">Session persists for this page</div>
			</div>
			<Button v-if="builderStore.isAIEnabled" variant="ghost" label="Clear" @click="clearSession" />
		</div>

		<div v-if="!builderStore.isAIEnabled" class="flex flex-1 flex-col items-start gap-3 p-4">
			<p class="text-sm text-ink-gray-6">Configure an AI API key in Builder Settings to use chat.</p>
			<Button variant="solid" label="Open Settings" @click="builderStore.openBuilderSettings" />
		</div>

		<template v-else>
			<div class="border-b border-outline-gray-1 px-4 py-3">
				<div class="mb-3 flex items-center gap-2">
					<Button
						:variant="scope === 'page' ? 'solid' : 'ghost'"
						label="Page"
						class="text-xs"
						@click="scope = 'page'" />
					<Button
						:variant="scope === 'selection' ? 'solid' : 'ghost'"
						label="Selection"
						:disabled="!selectedBlock"
						class="text-xs"
						@click="scope = 'selection'" />
				</div>
				<div
					class="rounded-md border border-outline-gray-1 bg-surface-gray-1 px-3 py-2 text-xs text-ink-gray-6">
					{{ contextLabel }}
				</div>
			</div>

			<div ref="messageContainer" class="no-scrollbar flex-1 space-y-3 overflow-y-auto px-4 py-4">
				<div
					v-if="!messages.length"
					class="rounded-lg border border-dashed border-outline-gray-2 p-4 text-sm text-ink-gray-5">
					Start with a page brief, or select a block and ask for an inline edit.
				</div>
				<div
					v-for="message in messages"
					:key="message.id"
					class="flex"
					:class="message.role === 'user' ? 'justify-end' : 'justify-start'">
					<div
						class="max-w-[88%] rounded px-3 py-2 text-p-sm shadow-sm"
						:class="
							message.role === 'user'
								? 'bg-surface-blue-2 text-ink-gray-9'
								: ' bg-surface-gray-1 text-ink-gray-8'
						">
						<div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
						<div class="mt-1 text-[11px] text-ink-gray-5">
							{{ messageLabel(message) }}
						</div>
					</div>
				</div>
			</div>

			<div class="border-t border-outline-gray-1 p-4">
				<Textarea
					v-model="prompt"
					:rows="4"
					class="w-full text-sm"
					placeholder="Ask AI to create or edit this page..."
					@keydown.meta.enter="submitPrompt"
					@keydown.ctrl.enter="submitPrompt" />
				<div class="mt-3 flex items-center justify-between gap-2">
					<div class="truncate text-xs text-ink-gray-5">
						{{ progressMessage || modelLabel }}
					</div>
					<Button
						variant="solid"
						label="Send"
						icon-right="arrow-up"
						:disabled="!canSubmit"
						:loading="isSubmitting"
						@click="submitPrompt" />
				</div>
			</div>
		</template>
	</div>
</template>

<script setup lang="ts">
import type Block from "@/block";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { getBlockInstance, getBlockObject } from "@/utils/helpers";
import { useLocalStorage } from "@vueuse/core";
import { Button, createResource, Textarea } from "frappe-ui";
// @ts-ignore
import yaml from "js-yaml";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

interface AIModel {
	name: string;
	label: string;
	vision?: boolean;
}

interface AIProvider {
	provider: string;
	models: AIModel[];
}

interface ChatMessage {
	id: string;
	role: "user" | "assistant";
	content: string;
	message_type?: string;
	task_type?: string | null;
	block_id?: string | null;
	created_at?: string;
	metadata?: Record<string, any>;
}

const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();
const pageStore = usePageStore();
const route = useRoute();

const prompt = ref("");
const progressMessage = ref("");
const isSubmitting = ref(false);
const availableModels = ref<AIProvider[]>([]);
const selectedModel = useLocalStorage("ai-selected-model", "");
const sessionId = ref("");
const messages = ref<ChatMessage[]>([]);
const scope = ref<"page" | "selection">("page");
const streamingContent = ref("");
const remoteTaskType = ref<string | null>(null);
const remoteBlockId = ref<string | null>(null);
const pendingAssistantId = ref<string | null>(null);
const messageContainer = ref<HTMLElement | null>(null);

const pageId = computed(() => route.params.pageId as string);
const currentProviderModels = computed(() => {
	const found = availableModels.value.find((provider) => provider.provider === "openrouter");
	return found?.models || [];
});
const selectedBlock = computed<Block | null>(() => {
	return (
		canvasStore.editableBlock || (canvasStore.activeCanvas?.selectedBlocks?.[0] as Block | undefined) || null
	);
});
const rootBlock = computed<Block | null>(() => pageStore.pageBlocks[0] || null);
const modelLabel = computed(() => {
	return (
		currentProviderModels.value.find((model) => model.name === selectedModel.value)?.label || "Select model"
	);
});
const canSubmit = computed(() => {
	return !!prompt.value.trim() && !isSubmitting.value && !!selectedModel.value;
});
const contextLabel = computed(() => {
	if (scope.value === "selection" && selectedBlock.value) {
		return `Editing selected block: ${
			selectedBlock.value.blockName || selectedBlock.value.element || selectedBlock.value.blockId
		}`;
	}
	return "Working against the full page draft";
});

watch(
	currentProviderModels,
	(models) => {
		const isValid = models.some((model) => model.name === selectedModel.value);
		if (models.length && (!selectedModel.value || !isValid)) {
			selectedModel.value = models[0].name;
		}
	},
	{ immediate: true },
);

watch(selectedBlock, (block) => {
	if (!block && scope.value === "selection") {
		scope.value = "page";
	}
});

watch(
	() => [messages.value.length, progressMessage.value],
	async () => {
		await nextTick();
		messageContainer.value?.scrollTo({ top: messageContainer.value.scrollHeight });
	},
);

watch(pageId, async (newPageId, oldPageId) => {
	if (oldPageId) {
		detachListeners(oldPageId);
	}
	if (newPageId) {
		attachListeners(newPageId);
		resetTransientState();
		await loadSession();
	}
});

function resetTransientState() {
	progressMessage.value = "";
	streamingContent.value = "";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
	pendingAssistantId.value = null;
	isSubmitting.value = false;
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

function replacePendingAssistant(content: string, metadata: Record<string, any> = {}) {
	if (!pendingAssistantId.value) return;
	const index = messages.value.findIndex((message) => message.id === pendingAssistantId.value);
	if (index === -1) return;
	messages.value[index] = {
		...messages.value[index],
		content,
		metadata: {
			...messages.value[index].metadata,
			...metadata,
		},
	};
}

function messageLabel(message: ChatMessage) {
	const scopeLabel = message.metadata?.scope === "selection" ? "selection" : "page";
	if (message.role === "user") {
		return scopeLabel;
	}
	return message.metadata?.status || message.task_type || "assistant";
}

async function loadSession() {
	if (!pageId.value || !builderStore.isAIEnabled) return;
	const result = await createResource({
		url: "builder.ai_page_generator.get_ai_session",
		makeParams: () => ({
			page_id: pageId.value,
			model: selectedModel.value,
		}),
	}).submit();
	const session = result as { session_id: string; messages: ChatMessage[] };
	sessionId.value = session.session_id;
	messages.value = (session.messages || []).map((message) => ({
		...message,
		role: message.role === "user" ? "user" : "assistant",
	}));
}

async function clearSession() {
	if (!pageId.value) return;
	const result = await createResource({
		url: "builder.ai_page_generator.clear_ai_session",
		makeParams: () => ({ page_id: pageId.value }),
	}).submit();
	const session = result as { session_id: string; messages: ChatMessage[] };
	sessionId.value = session.session_id;
	messages.value = session.messages || [];
	resetTransientState();
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
		if (replacement.attributes) {
			root.attributes = { ...root.attributes, ...replacement.attributes };
		}
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

function applyPageStream() {
	const block = parseBlock(streamingContent.value);
	if (!block) return;
	try {
		pageStore.pageBlocks = [getBlockInstance(block)];
		canvasStore.activeCanvas?.setRootBlock(pageStore.pageBlocks[0] as Block, false);
	} catch {}
}

function applyModifyStream() {
	const block = parseBlock(streamingContent.value);
	const targetId = remoteBlockId.value || selectedBlock.value?.blockId;
	if (!block || !targetId || !rootBlock.value) return;
	try {
		replaceBlockInTree(rootBlock.value, targetId, block);
	} catch {}
}

function eventName(base: string, targetPageId = pageId.value) {
	return targetPageId ? `${base}_${targetPageId}` : base;
}

function onProgress(data: { message?: string; task_type?: string; block_id?: string }) {
	isSubmitting.value = true;
	progressMessage.value = data.message || progressMessage.value;
	if (data.task_type) remoteTaskType.value = data.task_type;
	if (data.block_id) remoteBlockId.value = data.block_id;
	replacePendingAssistant(progressMessage.value || "Working...", { status: "running" });
}

function onStream(data: { chunk?: string; task_type?: string; block_id?: string }) {
	if (!data.chunk) return;
	isSubmitting.value = true;
	streamingContent.value += data.chunk;
	if (data.task_type) remoteTaskType.value = data.task_type;
	if (data.block_id) remoteBlockId.value = data.block_id;
	if (remoteTaskType.value || scope.value === "selection") {
		applyModifyStream();
	} else {
		applyPageStream();
	}
}

async function onComplete(data: { message?: string }) {
	isSubmitting.value = false;
	progressMessage.value = data.message || "Applied update";
	replacePendingAssistant(progressMessage.value, { status: "complete" });
	pageStore.savePage();
	prompt.value = "";
	streamingContent.value = "";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
	await loadSession();
	window.setTimeout(() => {
		progressMessage.value = "";
		pendingAssistantId.value = null;
	}, 1200);
}

async function onError(data: { message?: string }) {
	isSubmitting.value = false;
	progressMessage.value = "";
	replacePendingAssistant(data.message || "Request failed", { status: "error" });
	streamingContent.value = "";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
	await loadSession();
	pendingAssistantId.value = null;
}

// ---------------------------------------------------------------------------
// Agent helpers — targeted block-tree mutations driven by tool calls
// ---------------------------------------------------------------------------

function findBlockInTree(blockId: string, root: Block | null = rootBlock.value): Block | null {
	if (!root) return null;
	if (root.blockId === blockId) return root;
	for (const child of root.children || []) {
		const found = findBlockInTree(blockId, child as Block);
		if (found) return found;
	}
	return null;
}

function applyToolOperation(toolName: string, args: Record<string, any>) {
	if (toolName === "update_block") {
		const block = findBlockInTree(args.block_id);
		if (!block) return;
		// Use setBaseStyle for each property to maintain reactivity
		if (args.base_styles) {
			Object.entries(args.base_styles).forEach(([key, value]) => {
				block.setBaseStyle(key as any, value as StyleValue);
			});
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
		// Use setAttribute for attributes
		if (args.attributes) {
			Object.entries(args.attributes).forEach(([key, value]) => {
				block.setAttribute(key, value as string | undefined);
			});
		}
		if (args.inner_text !== undefined) block.innerText = args.inner_text;
		if (args.inner_html !== undefined) block.innerHTML = args.inner_html;
		if (args.element !== undefined) block.element = args.element;
		if (args.classes !== undefined) block.classes = args.classes;
		return;
	}

	if (toolName === "add_block") {
		const parent = findBlockInTree(args.parent_block_id);
		if (!parent) return;
		const newBlockOpts = convertYAMLtoBlock(args.block as Record<string, any>);
		const newBlock = getBlockInstance(newBlockOpts);
		if (args.after_block_id) {
			const sibling = findBlockInTree(args.after_block_id, parent);
			if (sibling) {
				parent.addChildAfter(newBlock, sibling);
				return;
			}
		}
		const index = typeof args.index === "number" ? args.index : null;
		parent.addChild(newBlock, index);
		return;
	}

	if (toolName === "remove_block") {
		const block = findBlockInTree(args.block_id);
		if (!block) return;
		block.getParentBlock()?.removeChild(block);
		return;
	}

	if (toolName === "move_block") {
		const block = findBlockInTree(args.block_id);
		const newParent = findBlockInTree(args.new_parent_block_id);
		if (!block || !newParent) return;
		block.getParentBlock()?.removeChild(block);
		if (args.after_block_id) {
			const sibling = findBlockInTree(args.after_block_id, newParent);
			if (sibling) {
				newParent.addChildAfter(block, sibling);
				return;
			}
		}
		const index = typeof args.index === "number" ? args.index : null;
		newParent.addChild(block, index, false);
		return;
	}
}

function onAgentToolBatch(data: { operations?: Array<{ tool_name: string; args: Record<string, any> }> }) {
	if (!data.operations?.length) return;
	for (const op of data.operations) {
		try {
			applyToolOperation(op.tool_name, op.args);
		} catch (e) {
			console.warn(`[AI agent] tool "${op.tool_name}" failed:`, e);
		}
	}
	const n = data.operations.length;
	replacePendingAssistant(`Applied ${n} change${n !== 1 ? "s" : ""}…`, { status: "running" });
}

const listeners = {
	ai_generation_progress: onProgress,
	ai_generation_stream: onStream,
	ai_generation_complete: onComplete,
	ai_generation_error: onError,
	ai_modify_progress: onProgress,
	ai_modify_stream: onStream,
	ai_modify_complete: onComplete,
	ai_modify_error: onError,
	ai_agent_progress: onProgress,
	ai_agent_tool_batch: onAgentToolBatch,
	ai_agent_stream: onStream,
	ai_agent_complete: onComplete,
	ai_agent_error: onError,
};

function attachListeners(targetPageId: string) {
	Object.entries(listeners).forEach(([event, handler]) => {
		builderStore.realtime.on(eventName(event, targetPageId), handler);
	});
}

function detachListeners(targetPageId: string) {
	Object.entries(listeners).forEach(([event, handler]) => {
		builderStore.realtime.off(eventName(event, targetPageId), handler);
	});
}

function isGenerateMode() {
	if (scope.value === "selection") {
		return false;
	}
	return !rootBlock.value || !rootBlock.value.children?.length;
}

async function submitPrompt() {
	if (!canSubmit.value || !pageId.value) return;
	if (!sessionId.value) {
		await loadSession();
	}

	const userText = prompt.value.trim();
	const userMessage = buildLocalMessage("user", userText, { scope: scope.value });
	const assistantMessage = buildLocalMessage("assistant", "Working...", { status: "running" });
	messages.value.push(userMessage, assistantMessage);
	pendingAssistantId.value = assistantMessage.id;
	streamingContent.value = "";
	remoteTaskType.value = null;
	remoteBlockId.value = null;
	isSubmitting.value = true;

	const runGenerate = scope.value === "page" && isGenerateMode();
	// Page scope with existing blocks → agent tool-calling path
	const runAgent = scope.value === "page" && !runGenerate;

	const targetBlock = scope.value === "selection" ? selectedBlock.value : rootBlock.value;

	let url: string;
	let extraParams: Record<string, any> = {};

	if (runGenerate) {
		url = "builder.ai_page_generator.generate_page_from_prompt";
	} else if (runAgent) {
		url = "builder.ai_page_generator.run_agent_from_prompt";
		extraParams = { page_context: JSON.stringify(getBlockObject(rootBlock.value as Block)) };
	} else {
		// selection scope — focused YAML replacement
		url = "builder.ai_page_generator.modify_section_from_prompt";
		extraParams = { block_context: JSON.stringify(getBlockObject(targetBlock as Block)) };
	}

	try {
		const result = await createResource({
			url,
			makeParams: () => ({
				prompt: userText,
				page_id: pageId.value,
				model: selectedModel.value,
				session_id: sessionId.value,
				...extraParams,
			}),
		}).submit();
		const response = result as { session_id?: string };
		if (response.session_id) {
			sessionId.value = response.session_id;
		}
	} catch (error) {
		await onError({ message: error instanceof Error ? error.message : "Request failed" });
	}
}

onMounted(async () => {
	if (pageId.value) {
		attachListeners(pageId.value);
	}
	createResource({
		url: "builder.ai_page_generator.get_ai_models",
		auto: true,
		onSuccess: (data: AIProvider[]) => {
			availableModels.value = data;
		},
	});
	await loadSession();
});

onUnmounted(() => {
	if (pageId.value) {
		detachListeners(pageId.value);
	}
});
</script>
