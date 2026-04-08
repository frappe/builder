<template>
	<div class="flex h-full min-h-full flex-col bg-surface-white">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-4 py-3">
			<div>
				<div class="text-sm font-medium text-ink-gray-9">Bob AI</div>
				<div class="text-p-xs text-ink-gray-5">Session persists for this page</div>
			</div>
			<Button v-if="builderStore.isAIEnabled" variant="subtle" label="Clear" @click="clearSession" />
		</div>

		<div v-if="!builderStore.isAIEnabled" class="flex flex-1 flex-col items-start gap-3 p-4">
			<p class="text-sm text-ink-gray-6">Configure an AI API key in Builder Settings to use chat.</p>
			<Button variant="solid" label="Open Settings" @click="builderStore.openBuilderSettings" />
		</div>

		<template v-else>
			<div class="border-b border-outline-gray-1 px-4 py-3">
				<OptionToggle v-model="scope" :options="scopeOptions" />
				<!-- <div
					class="rounded-md border border-outline-gray-1 bg-surface-gray-1 px-3 py-2 text-xs text-ink-gray-6">
					{{ contextLabel }}
				</div> -->
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
						class="max-w-[88%] text-p-sm"
						:class="message.role === 'user' ? 'rounded-md border px-3 py-2 text-ink-gray-9 shadow-sm' : ''">
						<div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
						<div class="mt-1 text-[11px] text-ink-gray-5">
							{{ messageLabel(message) }}
						</div>
						<Button
							v-if="message.metadata?.undoScripts?.length"
							class="mt-1"
							variant="ghost"
							size="sm"
							label="Undo script"
							@click="undoAgentScript(message)" />
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
import { AIChatController } from "@/components/AIChatController";
import OptionToggle from "@/components/Controls/OptionToggle.vue";
import useBuilderStore from "@/stores/builderStore";
import { Button, Textarea } from "frappe-ui";
import { onMounted, onUnmounted } from "vue";

const chat = new AIChatController();

const {
	prompt,
	progressMessage,
	isSubmitting,
	scope,
	messageContainer,
	messages,
	selectedModel,
	modelLabel,
	scopeOptions,
	canSubmit,
} = chat;
const { clearSession, submitPrompt, undoAgentScript } = chat;
const messageLabel = chat.messageLabel.bind(chat);
const builderStore = useBuilderStore();

onMounted(() => chat.mount());
onUnmounted(() => chat.unmount());
</script>
