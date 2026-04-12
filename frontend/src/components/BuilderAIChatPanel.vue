<template>
	<div class="flex h-full min-h-full flex-col bg-surface-white">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
			<div class="flex flex-col gap-1">
				<div class="mt-1 text-sm font-semibold text-ink-gray-9">Bob AI</div>
				<div class="text-p-xs leading-4 text-ink-gray-5">Session persists for this page</div>
			</div>
			<button
				v-if="builderStore.isAIEnabled && messages.length"
				class="text-xs text-ink-gray-4 hover:text-ink-gray-9"
				@click="clearSession">
				Clear
			</button>
		</div>

		<div v-if="!builderStore.isAIEnabled" class="flex flex-1 flex-col items-start gap-3 p-4">
			<p class="text-sm text-ink-gray-6">Configure an AI API key in Builder Settings to use chat.</p>
			<Button variant="solid" label="Open Settings" @click="builderStore.openBuilderSettings" />
		</div>

		<template v-else>
			<!-- <div class="border-b border-outline-gray-1 px-4 py-3">
				<OptionToggle v-model="scope" :options="scopeOptions" />
			</div> -->

			<div ref="messageContainer" class="no-scrollbar flex-1 space-y-4 overflow-y-auto px-4 py-4">
				<div
					v-if="!messages.length"
					class="flex h-full flex-col items-center justify-center gap-2 pb-8 text-center">
					<SparklesIcon class="size-8 text-ink-gray-3" />
					<p class="text-xs text-ink-gray-4">Chat with Bob to create or edit page</p>
				</div>
				<div
					v-for="message in messages"
					:key="message.id"
					class="flex flex-col"
					:class="message.role === 'user' ? 'items-end' : 'items-start'">
					<div
						class="w-fit text-p-sm"
						:class="[
							message.role === 'user'
								? 'max-w-[88%] rounded-md border px-3 py-2 text-ink-gray-8 shadow-sm'
								: 'max-w-full',
							message.role === 'assistant' && message.metadata?.status === 'running'
								? 'animate-pulse text-ink-gray-5'
								: 'text-ink-gray-8',
						]">
						<div
							v-if="message.role === 'assistant'"
							class="ai-prose prose prose-sm max-w-none text-p-sm"
							v-html="renderMarkdown(message.content)" />
						<div v-else>
							<div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
						</div>
						<Button
							v-if="message.metadata?.undoScripts?.length"
							class="mt-1"
							variant="ghost"
							size="sm"
							label="Undo script"
							@click="undoAgentScript(message)" />
						<AIAffectedItems
							v-if="message.metadata?.affectedBlocks?.length || message.metadata?.affectedScripts?.length"
							:affected-blocks="message.metadata.affectedBlocks || []"
							:affected-scripts="message.metadata.affectedScripts || []"
							@select-block="selectBlockById"
							@open-script="openScriptByName" />
						<!-- Clarification options -->
						<div
							v-if="message.metadata?.status === 'clarification' && message.metadata?.options?.length"
							class="mt-2 flex flex-wrap gap-1.5">
							<button
								v-for="option in message.metadata.options"
								:key="option"
								:disabled="isSubmitting"
								class="rounded-full border border-outline-gray-2 bg-surface-white px-2.5 py-1 text-[11px] text-ink-gray-7 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-2 disabled:cursor-not-allowed disabled:opacity-50"
								@click="selectOption(option)">
								{{ option }}
							</button>
						</div>
					</div>
					<!-- Block + image chips below the bubble -->
					<div
						v-if="
							message.role === 'user' &&
							(message.metadata?.selectedBlockContext?.length || message.metadata?.attachedImageUrl)
						"
						class="mt-1 flex max-w-[88%] flex-wrap items-center gap-1">
						<!-- image chip -->
						<span
							v-if="message.metadata?.attachedImageUrl"
							class="inline-flex items-center gap-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-6">
							<img :src="message.metadata.attachedImageUrl" class="h-3 w-3 rounded object-cover" alt="" />
							Image
						</span>
						<!-- block chips -->
						<button
							v-for="block in getVisibleChips(message)"
							:key="block.id"
							class="inline-flex items-center rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-6 transition-colors hover:bg-surface-gray-3 hover:text-ink-gray-8"
							@click="selectBlockById(block.id)">
							{{ block.label }}
						</button>
						<button
							v-if="(message.metadata?.selectedBlockContext?.length ?? 0) > MAX_VISIBLE_CHIPS"
							class="inline-flex items-center rounded bg-surface-gray-2 px-1.5 py-0.5 text-[10px] text-ink-gray-5 transition-colors hover:bg-surface-gray-3"
							@click="toggleChips(message.id)">
							{{
								expandedMessages.has(message.id)
									? "Show less"
									: `+${(message.metadata?.selectedBlockContext?.length ?? 0) - MAX_VISIBLE_CHIPS} more`
							}}
						</button>
					</div>
				</div>
			</div>

			<div class="border-t border-outline-gray-1 p-4">
				<div v-if="selectedBlocks.length" class="mb-2 flex flex-wrap items-center gap-1.5">
					<span class="text-xs text-ink-gray-5">Selections:</span>
					<span
						v-for="block in selectedBlocks"
						:key="block.blockId"
						class="inline-flex items-center gap-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">
						{{ block.blockName || block.element }}
					</span>
				</div>
				<Transition name="fade">
					<div v-if="imagePreviewUrl" class="mb-1.5 flex flex-wrap gap-1">
						<span
							class="inline-flex items-center gap-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">
							<img :src="imagePreviewUrl" class="h-3 w-3 rounded object-cover" alt="" />
							<span class="max-w-[120px] truncate">{{ imageFileName }}</span>
							<button
								type="button"
								class="hover:text-ink-red-7 ml-0.5 flex items-center text-ink-gray-4"
								title="Remove image"
								@click="clearImage">
								<FeatherIcon name="x" class="h-3 w-3" />
							</button>
						</span>
					</div>
				</Transition>
				<div
					class="relative"
					@paste.stop="handlePaste"
					@dragover.prevent="isDragging = isVisionModel ? true : isDragging"
					@dragleave="isDragging = false"
					@drop.prevent="handleDrop">
					<textarea
						v-model="prompt"
						rows="4"
						class="w-full resize-none rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1.5 text-sm text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-modals hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-not-allowed disabled:bg-surface-gray-1 disabled:text-ink-gray-5"
						:disabled="isSubmitting"
						placeholder="Ask to create or edit this page..."
						@keydown.meta.enter="submitPrompt"
						@keydown.ctrl.enter="submitPrompt" />
					<Transition name="fade">
						<div
							v-if="isDragging"
							class="border-outline-blue-3 bg-surface-blue-1/60 pointer-events-none absolute inset-0 flex items-center justify-center rounded-md border-2 border-dashed">
							<div class="text-ink-blue-4 flex items-center gap-1.5 text-xs font-medium">
								<FeatherIcon name="image" class="h-3.5 w-3.5" />
								Drop image to attach
							</div>
						</div>
					</Transition>
					<span
						v-if="isVisionModel && !imagePreviewUrl && !isDragging"
						class="pointer-events-none absolute bottom-3 right-2 select-none text-[10px] text-ink-gray-4">
						Paste or drop image
					</span>
				</div>
				<div class="mt-2 flex items-center justify-between gap-2">
					<div class="flex min-w-0 items-center gap-1">
						<Dropdown :options="[{ label: 'Select Model', disabled: true }, ...modelOptions]">
							<Button variant="ghost" icon-right="chevron-up" :label="modelLabel" />
						</Dropdown>
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
import AIAffectedItems from "@/components/AIAffectedItems.vue";
import { AIChatController, type ChatMessage } from "@/components/AIChatController";
import SparklesIcon from "@/components/Icons/Sparkles.vue";
import useBuilderStore from "@/stores/builderStore";
import { Button, Dropdown, FeatherIcon } from "frappe-ui";
import { marked } from "marked";
import { onMounted, onUnmounted, ref, watch } from "vue";

marked.use({ breaks: true, gfm: true });

function renderMarkdown(content: string): string {
	return marked.parse(content) as string;
}

const chat = new AIChatController();

const { prompt, progressMessage, isSubmitting, messages, modelLabel, modelOptions, canSubmit } = chat;
const { clearSession, submitPrompt, undoAgentScript, selectOption } = chat;
const { selectBlockById, openScriptByName } = chat;
const { selectedBlocks } = chat;
const { imagePreviewUrl, imageFileName, isDragging, isVisionModel } = chat;
const { clearImage, attachImageFile } = chat;
const builderStore = useBuilderStore();

const messageContainer = ref<HTMLElement | null>(null);
watch(
	messageContainer,
	(el) => {
		chat.messageContainer.value = el;
	},
	{ immediate: true },
);

onMounted(() => chat.mount());
onUnmounted(() => chat.unmount());

function handlePaste(event: ClipboardEvent) {
	if (!isVisionModel.value) return;
	const items = Array.from(event.clipboardData?.items || []);
	const imageItem = items.find((item) => item.type.startsWith("image/"));
	if (!imageItem) return;
	event.preventDefault();
	const file = imageItem.getAsFile();
	if (file) attachImageFile(file);
}

function handleDrop(event: DragEvent) {
	isDragging.value = false;
	if (!isVisionModel.value) return;
	const file = Array.from(event.dataTransfer?.files || []).find((f) => f.type.startsWith("image/"));
	if (file) attachImageFile(file);
}

const MAX_VISIBLE_CHIPS = 3;
const expandedMessages = ref(new Set<string>());

function getVisibleChips(message: ChatMessage) {
	const blocks: { id: string; label: string }[] = message.metadata?.selectedBlockContext || [];
	if (expandedMessages.value.has(message.id)) return blocks;
	return blocks.slice(0, MAX_VISIBLE_CHIPS);
}

function toggleChips(messageId: string) {
	const next = new Set(expandedMessages.value);
	if (next.has(messageId)) next.delete(messageId);
	else next.add(messageId);
	expandedMessages.value = next;
}
</script>

<style>
.ai-prose {
	--tw-prose-body: var(--ink-gray-8);
	--tw-prose-headings: var(--ink-gray-9);
	--tw-prose-bold: var(--ink-gray-9);
	--tw-prose-code: var(--ink-gray-8);
	--tw-prose-links: var(--ink-gray-9);
	--tw-prose-bullets: var(--ink-gray-4);
	--tw-prose-hr: var(--outline-gray-1);
	--tw-prose-quotes: var(--ink-gray-6);
	--tw-prose-quote-borders: var(--outline-gray-2);
}
.ai-prose p:first-child {
	margin-top: 0;
}
.ai-prose p:last-child {
	margin-bottom: 0;
}
.ai-prose code {
	background: var(--surface-gray-2);
	border-radius: 0.25rem;
	padding: 0.1em 0.35em;
	font-size: 0.8em;
}
.ai-prose code::before,
.ai-prose code::after {
	content: none;
}
.ai-prose pre {
	background: var(--surface-gray-2) !important;
	border-radius: 0.375rem;
}
</style>
