<template>
	<div class="flex h-full min-h-full flex-col bg-surface-white">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-3">
			<div>
				<div class="text-sm font-medium text-ink-gray-9">Bob AI</div>
				<div class="text-p-xs text-ink-gray-5">Session persists for this page</div>
			</div>
			<Button v-if="builderStore.isAIEnabled" variant="ghost" label="Clear" @click="clearSession" />
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
					v-for="message in messages"
					:key="message.id"
					class="flex"
					:class="message.role === 'user' ? 'justify-end' : 'justify-start'">
					<div
						class="max-w-[88%] text-p-sm"
						:class="[
							message.role === 'user' ? 'rounded-md border px-3 py-2 text-ink-gray-8 shadow-sm' : '',
							message.role === 'assistant' && message.metadata?.status === 'running'
								? 'animate-pulse text-ink-gray-5'
								: 'text-ink-gray-8',
						]">
						<div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
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
				<textarea
					v-model="prompt"
					rows="4"
					class="w-full resize-none rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1.5 text-sm text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-modals hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-white focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-not-allowed disabled:bg-surface-gray-1 disabled:text-ink-gray-5"
					:disabled="isSubmitting"
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
import AIAffectedItems from "@/components/AIAffectedItems.vue";
import { AIChatController } from "@/components/AIChatController";
import useBuilderStore from "@/stores/builderStore";
import { Button } from "frappe-ui";
import { onMounted, onUnmounted, ref, watch } from "vue";

const chat = new AIChatController();

const { prompt, progressMessage, isSubmitting, messages, modelLabel, canSubmit, pageId } = chat;
const { clearSession, submitPrompt, undoAgentScript } = chat;
const { selectBlockById, openScriptByName } = chat;
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
