<template>
	<div class="flex h-full min-h-full flex-col bg-surface-white">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
			<div>
				<div class="text-sm font-semibold text-ink-gray-9">Bob AI</div>
				<div class="text-p-xs text-ink-gray-5">Session persists for this page</div>
			</div>
			<button
				v-if="builderStore.isAIEnabled"
				class="text-xs text-ink-gray-4 hover:text-ink-gray-7"
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
					class="flex"
					:class="message.role === 'user' ? 'justify-end' : 'justify-start'">
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
						<div v-else class="whitespace-pre-wrap break-words">{{ message.content }}</div>
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
					</div>
				</div>
			</div>

			<div class="border-t border-outline-gray-1 p-4">
				<div
					v-if="selectedBlocks.length && includeSelection"
					class="mb-2 flex flex-wrap items-center gap-1.5">
					<span class="text-xs text-ink-gray-5">Focusing on:</span>
					<span
						v-for="block in selectedBlocks"
						:key="block.blockId"
						class="inline-flex items-center gap-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">
						{{ block.blockName || block.element }}
					</span>
					<button
						class="ml-auto text-xs text-ink-gray-4 hover:text-ink-gray-7"
						title="Don't send selection as context"
						@click="includeSelection = false">
						✕ Clear
					</button>
				</div>
				<textarea
					v-model="prompt"
					rows="4"
					class="w-full resize-none rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1.5 text-sm text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-modals hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-not-allowed disabled:bg-surface-gray-1 disabled:text-ink-gray-5"
					:disabled="isSubmitting"
					placeholder="Ask to create or edit this page..."
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
import AIAffectedItems from "@/components/AIAffectedItems.vue";
import { AIChatController } from "@/components/AIChatController";
import SparklesIcon from "@/components/Icons/Sparkles.vue";
import useBuilderStore from "@/stores/builderStore";
import { Button } from "frappe-ui";
import { marked } from "marked";
import { onMounted, onUnmounted, ref, watch } from "vue";

marked.use({ breaks: true, gfm: true });

function renderMarkdown(content: string): string {
	return marked.parse(content) as string;
}

const chat = new AIChatController();

const { prompt, progressMessage, isSubmitting, messages, modelLabel, canSubmit, pageId } = chat;
const { clearSession, submitPrompt, undoAgentScript } = chat;
const { selectBlockById, openScriptByName } = chat;
const { selectedBlocks, includeSelection } = chat;
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
