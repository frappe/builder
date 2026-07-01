<template>
	<div class="bg-surface-white flex h-full min-h-full flex-col">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
			<div class="flex flex-col gap-1">
				<div class="mt-1 text-sm font-semibold text-ink-gray-9">Bob AI</div>
				<div class="text-p-xs leading-4 text-ink-gray-5">Session persists for this page</div>
			</div>
			<Button
				v-if="builderStore.isAIEnabled && messages.length"
				variant="ghost"
				size="sm"
				label="Clear"
				@click="clearSession" />
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
						<div
							v-if="message.role === 'assistant'"
							class="ai-prose prose prose-sm max-w-none break-words text-p-sm"
							v-html="renderMarkdown(message.content)" />
						<div v-else>
							<div class="whitespace-pre-wrap break-words">{{ message.content }}</div>
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
						<!-- Plan summary card -->
						<div
							v-if="message.metadata?.status === 'plan_summary'"
							class="mt-2 w-full rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
							<ul class="m-0 list-none space-y-1 p-0">
								<li
									v-for="section in message.metadata.sections"
									:key="section"
									class="flex items-start gap-2 text-p-sm leading-snug text-ink-gray-7">
									<span class="mt-[6px] size-1 shrink-0 rounded-full bg-surface-gray-4" />
									<span class="min-w-0 break-words">{{ section }}</span>
								</li>
							</ul>
							<div v-if="message.metadata.palette" class="mt-2.5 border-t border-outline-gray-1 pt-2.5">
								<div v-if="paletteColors(message.metadata.palette).length" class="mb-1 flex flex-wrap gap-1">
									<span
										v-for="hex in paletteColors(message.metadata.palette)"
										:key="hex"
										class="size-3.5 rounded-full border border-outline-gray-2"
										:style="{ backgroundColor: hex }"
										:title="hex" />
								</div>
								<p class="text-xs leading-snug text-ink-gray-5">{{ message.metadata.palette }}</p>
							</div>
							<!-- Action buttons — only on last message -->
							<template v-if="message.id === lastMessageId">
								<p class="mb-2 mt-2.5 text-xs text-ink-gray-5">
									Refine the plan below, or go ahead and create the page.
								</p>
								<button
									:disabled="isSubmitting"
									class="rounded-full border border-violet-300 bg-violet-50 px-3 py-1 text-xs font-medium text-violet-700 transition-colors hover:bg-violet-100 disabled:cursor-not-allowed disabled:opacity-50"
									@click="approvePlan">
									✦ Create Page
								</button>
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
						<!-- Clarification options -->
						<div
							v-if="message.metadata?.status === 'clarification' && message.metadata?.options?.length"
							class="mt-3 flex w-full flex-wrap gap-3">
							<button
								v-for="(option, idx) in message.metadata.options"
								:key="option"
								:disabled="isSubmitting"
								class="group flex flex-1 basis-48 flex-col items-start gap-2 rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2.5 text-left transition-all hover:border-outline-gray-3 hover:bg-surface-gray-2 disabled:cursor-not-allowed disabled:opacity-50"
								@click="selectOption(option)">
								<!-- Color palette swatches -->
								<span
									v-if="message.metadata.previews?.[idx]?.colors?.length"
									class="flex shrink-0 overflow-hidden rounded border border-black/10">
									<span
										v-for="color in message.metadata.previews[idx].colors.slice(0, 5)"
										:key="color"
										class="size-3.5"
										:style="{ backgroundColor: color }" />
								</span>
								<span class="text-p-sm font-medium leading-snug text-ink-gray-8">
									{{ optionParts(option).label }}
								</span>
								<span
									v-if="optionParts(option).desc"
									class="line-clamp-4 text-xs leading-snug text-ink-gray-5">
									{{ optionParts(option).desc }}
								</span>
							</button>
							<!-- Type-your-own nudge: only on last message -->
							<p v-if="message.id === lastMessageId" class="mt-1 text-xs text-ink-gray-4">
								Or describe something different below
							</p>
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
import { AIChatController, type ChatMessage } from "@/components/AIChatController";
import AIDebugPanel from "@/components/AIDebugPanel.vue";
import Dialog from "@/components/Controls/Dialog.vue";
import SparklesIcon from "@/components/Icons/Sparkles.vue";
import WebPagePresetPicker from "@/components/WebPagePresetPicker.vue";
import useBuilderStore from "@/stores/builderStore";
import DOMPurify from "dompurify";
import { Button, Dropdown, Popover, Tooltip } from "frappe-ui";
import { marked } from "marked";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

marked.use({ breaks: true, gfm: true });

function renderMarkdown(content: string): string {
	return DOMPurify.sanitize(marked.parse(content) as string, {
		ALLOWED_TAGS: [
			"p",
			"br",
			"strong",
			"em",
			"code",
			"pre",
			"ul",
			"ol",
			"li",
			"a",
			"h1",
			"h2",
			"h3",
			"h4",
			"blockquote",
			"hr",
			"span",
		],
		ALLOWED_ATTR: ["href", "target", "rel", "class"],
		ADD_ATTR: ["target"],
	});
}

const chat = new AIChatController();

const { prompt, isSubmitting, isCancelling, messages, modelLabel, modelOptions, canSubmit } = chat;
const { clearSession, revertTurn, selectOption, approvePlan } = chat;
const { selectBlockById, openScriptByName } = chat;
const { selectedBlocks } = chat;
const { imagePreviewUrl, imageFileName, isDragging, isVisionModel } = chat;
const { clearImage, attachImageFile } = chat;

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

/** Extract hex colour codes from a palette description for swatch previews. */
function paletteColors(palette: string): string[] {
	return palette.match(/#[0-9a-fA-F]{3,8}\b/g) || [];
}

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

/** Split a clarification option like "Editorial — asymmetric, serif headlines" or
 * "Warm Heritage (cream, terracotta)" into a bold label + muted description so
 * richer design-direction options stay readable instead of being truncated. */
function optionParts(option: string): { label: string; desc: string } {
	const dash = option.search(/\s[—–-]\s/);
	if (dash !== -1) {
		return {
			label: option.slice(0, dash).trim(),
			desc: option
				.slice(dash)
				.replace(/^\s[—–-]\s/, "")
				.trim(),
		};
	}
	const paren = option.indexOf(" (");
	if (paren !== -1 && option.trimEnd().endsWith(")")) {
		return {
			label: option.slice(0, paren).trim(),
			desc: option
				.slice(paren + 2)
				.replace(/\)\s*$/, "")
				.trim(),
		};
	}
	return { label: option.trim(), desc: "" };
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
