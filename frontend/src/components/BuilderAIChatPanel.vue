<template>
	<!-- Floating status: a build is streaming somewhere the user isn't looking —
	     another chat writing to THIS page (watch-live), or this chat's agent
	     building a DIFFERENT page. Teleported so it shows whichever tab is open. -->
	<!-- Top-center, solid dark: bottom-center is the canvas zoom pill's spot,
	     and a build indicator must not be missable. -->
	<Teleport to="body">
		<div
			v-if="foreignBuild"
			class="fixed left-1/2 top-14 z-50 flex -translate-x-1/2 items-center gap-2.5 rounded-full bg-zinc-900 px-4 py-2.5 text-p-sm font-medium text-white shadow-xl ring-1 ring-white/10">
			<span class="size-2 animate-pulse rounded-full bg-surface-amber-4" />
			<template v-if="foreignBuild.targetPage">
				Bob is building another page
				<router-link
					:to="{ name: 'builder', params: { pageId: foreignBuild.targetPage } }"
					class="text-white underline underline-offset-2">
					View
				</router-link>
			</template>
			<template v-else>
				Building this page from another chat
				<router-link
					v-if="foreignBuild.originPage"
					:to="{ name: 'builder', params: { pageId: foreignBuild.originPage } }"
					class="text-white underline underline-offset-2">
					Go back to that chat
				</router-link>
			</template>
		</div>
	</Teleport>
	<div class="bg-surface-white flex h-full min-h-full flex-col">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
			<div class="flex min-w-0 flex-col gap-1">
				<div class="mt-1 text-sm font-semibold text-ink-gray-9">Bob AI</div>
				<div class="truncate text-p-xs leading-4 text-ink-gray-5">{{ currentSessionTitle }}</div>
			</div>
			<div v-if="builderStore.isAIEnabled" class="flex shrink-0 items-center gap-1">
				<Tooltip text="New chat">
					<Button variant="ghost" size="sm" icon="lucide-plus" :disabled="isSubmitting" @click="newSession" />
				</Tooltip>
				<!-- Button sits directly in the Dropdown slot: a Tooltip wrapper breaks
				     the as-child trigger wiring (frappe-ui slot API). -->
				<Dropdown v-if="sessionOptions.length" :options="sessionOptions" :offset="6">
					<Button variant="ghost" size="sm" icon="lucide-history" title="Chats on this page" />
				</Dropdown>
			</div>
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
								? 'animate-shine'
								: 'text-ink-gray-8',
						]">
						<!-- ui-card messages persist the full card as text (for model replay);
						     the bubble shows only the short lead-in — the card renders the rest -->
						<div
							v-if="message.role === 'assistant'"
							class="ai-prose prose prose-sm max-w-none break-words text-p-sm"
							v-html="
								renderMarkdown(
									message.metadata?.status === 'ui'
										? (message.metadata?.text ?? message.content)
										: message.content,
								)
							" />
						<div v-else>
							<!-- Card-composed replies relay a long labelled text to the model;
							     the chat shows only the compact display line. -->
							<div class="whitespace-pre-wrap break-words">
								{{ message.metadata?.displayText || message.content }}
							</div>
						</div>
						<div
							v-if="
								message.metadata?.affectedBlocks?.length ||
								message.metadata?.affectedScripts?.length ||
								message.metadata?.revertSnapshot ||
								message.metadata?.debug
							"
							class="mb-2 mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-ink-gray-4">
							<AIAffectedItems
								v-if="message.metadata?.affectedBlocks?.length || message.metadata?.affectedScripts?.length"
								:affected-blocks="message.metadata.affectedBlocks || []"
								:affected-scripts="message.metadata.affectedScripts || []"
								@select-block="selectBlockById"
								@open-script="openScriptByName" />

							<button
								v-if="message.metadata?.revertSnapshot"
								class="inline-flex items-center gap-1 transition-colors hover:text-ink-gray-7"
								title="Revert the page to before this AI edit"
								@click="revertTurn(message)">
								<span class="lucide-rotate-ccw size-3" />
								Revert
							</button>
							<!-- Time taken + debugger trigger (full breakdown lives in the debug panel) -->
							<template v-if="message.metadata?.debug">
								<div class="ml-auto flex items-center gap-2">
									<span v-if="message.metadata.debug.elapsedMs" class="font-mono">
										took {{ formatDuration(message.metadata.debug.elapsedMs) }}
										<template v-if="message.metadata.debug.tokens?.cost">
											· ~{{ formatCost(message.metadata.debug.tokens.cost) }}
										</template>
									</span>
									<button
										class="inline-flex items-center transition-colors"
										:class="
											debugHasSignal(message.metadata.debug)
												? 'text-ink-amber-8 hover:text-ink-amber-7'
												: 'text-ink-gray-4 hover:text-ink-gray-7'
										"
										title="Inspect this turn (rounds, tools, tokens, why it stopped)"
										@click="openDebug(message.metadata.debug)">
										<span class="lucide-activity size-2.5" />
									</button>
								</div>
							</template>
						</div>
						<!-- Sensitive action — needs the user's OK -->
						<div
							v-if="message.metadata?.status === 'pending_action'"
							class="mt-2 w-full rounded-lg border border-outline-amber-2 bg-surface-amber-1 p-3">
							<p class="text-p-sm font-medium text-ink-gray-8">Needs your OK</p>
							<p class="mt-0.5 text-xs leading-snug text-ink-gray-6">
								{{ pendingPreview(message.metadata) }}
							</p>
							<div v-if="message.id === lastMessageId" class="mt-3 flex gap-2">
								<Button
									variant="solid"
									:loading="confirmingAction"
									@click="confirmPendingAction(message, 'apply')">
									Apply
								</Button>
								<Button
									variant="subtle"
									:disabled="confirmingAction"
									@click="confirmPendingAction(message, 'skip')">
									Skip
								</Button>
							</div>
						</div>
						<!-- Agent-composed UI card (present_ui) -->
						<AIUISpec
							v-if="message.metadata?.status === 'ui' && message.metadata?.ui?.length"
							:ui="message.metadata.ui"
							:interactive="message.id === lastMessageId"
							:disabled="isSubmitting"
							@submit="selectOption" />
						<!-- Parallel page-build progress (spawn_parallel_agents) -->
						<AITaskGroupCard
							v-if="message.metadata?.batchId && batches[message.metadata.batchId]"
							:batch="batches[message.metadata.batchId]"
							:publishing="publishingBatch"
							@cancel="cancelBatch"
							@publish="publishBatch" />
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
						<span class="block max-w-[8rem] truncate">{{ block.getBlockDescription() }}</span>
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
								class="ml-0.5 flex items-center text-ink-gray-4 hover:text-ink-red-7"
								title="Remove image"
								@click="clearImage">
								<span class="lucide-x h-3 w-3" />
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
						class="hover:border-outline-gray-modals focus:bg-surface-white w-full resize-none rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1.5 text-sm text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-not-allowed disabled:bg-surface-gray-1 disabled:text-ink-gray-5"
						:disabled="isSubmitting"
						placeholder="Ask to create or edit this page..."
						@keydown.meta.enter="submitPrompt"
						@keydown.ctrl.enter="submitPrompt" />
					<Transition name="fade">
						<div
							v-if="isDragging"
							class="pointer-events-none absolute inset-0 flex items-center justify-center rounded-md border-2 border-dashed border-outline-blue-3 bg-surface-blue-1/60">
							<div class="flex items-center gap-1.5 text-xs font-medium text-ink-blue-4">
								<span class="lucide-image h-3.5 w-3.5" />
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
					<div class="flex items-center gap-0.5">
						<Dropdown :options="modelOptions" side="top" :offset="6">
							<button
								class="flex h-7 max-w-[9rem] items-center gap-1.5 rounded px-1.5 text-ink-gray-5 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-8">
								<span class="lucide-cpu size-3.5 shrink-0" />
								<span class="truncate text-xs">{{ modelLabel }}</span>
							</button>
						</Dropdown>
						<Popover v-if="!messages.length" placement="top-start" :offset="6">
							<template #target="{ togglePopover }">
								<Tooltip :text="selectedPreset ? selectedPreset.name : 'Style Preset'" placement="top">
									<button
										class="flex size-7 items-center justify-center rounded text-ink-gray-5 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-8"
										:class="{ 'bg-surface-gray-2 text-ink-gray-8': selectedPreset }"
										@click="togglePopover">
										<span class="lucide-layout size-3.5" />
									</button>
								</Tooltip>
							</template>
							<template #body>
								<div class="bg-surface-white w-96 rounded-lg border border-outline-gray-2 p-3 shadow-lg">
									<WebPagePresetPicker v-model="selectedPreset" />
								</div>
							</template>
						</Popover>
					</div>
					<Button
						v-if="isSubmitting"
						variant="solid"
						icon="lucide-square"
						:loading="isCancelling"
						:title="isCancelling ? 'Cancelling…' : 'Cancel generation'"
						@click="chat.cancel" />
					<Button
						v-else
						variant="solid"
						icon="lucide-arrow-up"
						:disabled="!canSubmit"
						@click="submitPrompt" />
				</div>
			</div>
		</template>
		<Dialog title="Turn debug" size="3xl" v-model="debugOpen">
			<template #default>
				<AIDebugPanel :debug="debugData" />
			</template>
		</Dialog>
	</div>
</template>

<script setup lang="ts">
import AIAffectedItems from "@/components/AIAffectedItems.vue";
import AITaskGroupCard from "@/components/ai/AITaskGroupCard.vue";
import AIUISpec from "@/components/ai/AIUISpec.vue";
import { AIChatController, type ChatMessage } from "@/components/AIChatController";
import AIDebugPanel from "@/components/AIDebugPanel.vue";
import Dialog from "@/components/Controls/Dialog.vue";
import SparklesIcon from "@/components/Icons/Sparkles.vue";
import WebPagePresetPicker from "@/components/WebPagePresetPicker.vue";
import { formatCost } from "@/components/ai/format";
import { renderMarkdown } from "@/components/ai/markdown";
import useBuilderStore from "@/stores/builderStore";
import { Button, Dropdown, Popover, Tooltip } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

const chat = new AIChatController();

const { prompt, isSubmitting, isCancelling, messages, modelLabel, modelOptions, canSubmit } = chat;
const { revertTurn, selectOption } = chat;
const { sessions, sessionId, switchSession, newSession, deleteSession } = chat;

const currentSessionTitle = computed(() => {
	const current = sessions.value.find((s) => s.name === sessionId.value);
	return current?.title || "New chat";
});

/** VS Code-style session switcher: this page's chats (current one checked),
 * plus delete for the current chat. Titles are first prompts, so cap them —
 * the dropdown sizes to its longest label and would sprawl across the canvas. */
const truncateTitle = (title: string, max = 44) =>
	title.length > max ? title.slice(0, max - 1).trimEnd() + "…" : title;

const sessionOptions = computed(() => {
	if (!sessions.value.length) return [];
	return [
		...sessions.value.map((s) => ({
			label: truncateTitle(s.title || "New chat"),
			icon: s.name === sessionId.value ? "lucide-check" : "lucide-message-circle",
			onClick: () => switchSession(s.name),
		})),
		{ label: "Delete current chat", icon: "lucide-trash-2", onClick: deleteSession },
	];
});
const { selectBlockById, openScriptByName } = chat;
const { selectedBlocks } = chat;
const { imagePreviewUrl, imageFileName, isDragging, isVisionModel } = chat;
const { clearImage, attachImageFile } = chat;
const { batches, publishingBatch } = chat;
const { cancelBatch, publishBatch } = chat;
const { foreignBuild } = chat;

const confirmingAction = ref(false);
async function confirmPendingAction(message: ChatMessage, decision: "apply" | "skip") {
	confirmingAction.value = true;
	try {
		await chat.confirmPendingAction(message, decision);
	} finally {
		confirmingAction.value = false;
	}
}

/** Short human summary of a proposed sensitive action, shown on its confirm card. */
function pendingPreview(m: Record<string, any>): string {
	const p = m.payload || {};
	switch (m.kind) {
		case "create_doctype":
			return `Create a new DocType “${p.name}” with ${(p.fields || []).length} field(s).`;
		case "seed_sample_data":
			return `Insert ${(p.rows || []).length} sample record(s) into “${p.doctype}”.`;
		case "global_settings":
			return `Update site-wide settings (${Object.keys(p).join(", ")}). These load on every page.`;
		case "home_page":
			return `Set the site home page to “${p.route}”.`;
		case "publish_site":
			return "Publish all pages in this site.";
		default:
			return "Confirm this change?";
	}
}
const builderStore = useBuilderStore();

const lastMessageId = computed(() => messages.value.at(-1)?.id ?? null);

// --- Turn debugger ---------------------------------------------------------
const debugOpen = ref(false);
const debugData = ref<Record<string, any> | null>(null);
function openDebug(debug: Record<string, any>) {
	debugData.value = debug;
	debugOpen.value = true;
}
/** True when a turn had something noteworthy (truncation, repair, failures, cap) —
 * tints the debug trigger so problems are spottable without opening it. */
function debugHasSignal(debug: Record<string, any>): boolean {
	if (!debug) return false;
	return Boolean(
		debug.noopCorrected ||
			(debug.argsRepaired ?? 0) > 0 ||
			(debug.toolFailures?.length ?? 0) > 0 ||
			(debug.finishReasons || []).includes("length") ||
			debug.stopReason === "max_rounds" ||
			debug.stopReason === "noop_unbacked",
	);
}

/** Human-readable elapsed time, e.g. 950ms→"1s", 147900ms→"2m 28s". The full
 * token/round breakdown now lives in the debug panel, so the inline line is just this. */
function formatDuration(ms: number): string {
	const secs = Math.round((ms || 0) / 1000);
	if (secs < 60) return `${secs}s`;
	const mins = Math.floor(secs / 60);
	if (mins < 60) return secs % 60 ? `${mins}m ${secs % 60}s` : `${mins}m`;
	const hrs = Math.floor(mins / 60);
	return mins % 60 ? `${hrs}h ${mins % 60}m` : `${hrs}h`;
}

const selectedPreset = ref<{
	id: string;
	name: string;
	category: string;
	description: string;
	icon: string;
} | null>(null);

const submitPrompt = () => {
	if (selectedPreset.value) {
		// Pass preset as a structured system-level parameter, not appended user text
		chat.pendingStylePreset = `${selectedPreset.value.name}: ${selectedPreset.value.description}`;
		selectedPreset.value = null;
	}
	chat.submitPrompt();
};

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
@keyframes shine {
	from {
		background-position: 200% center;
	}
	to {
		background-position: -200% center;
	}
}
.animate-shine {
	background: linear-gradient(120deg, var(--ink-gray-6) 20%, var(--ink-gray-9) 50%, var(--ink-gray-6) 80%);
	background-size: 200% auto;
	-webkit-background-clip: text;
	background-clip: text;
	-webkit-text-fill-color: transparent;
	animation: shine 2.5s linear infinite;
}
</style>
