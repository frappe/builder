<template>
	<div class="flex h-full min-h-full flex-col bg-surface-base">
		<div class="flex items-center justify-between border-b border-outline-gray-1 px-3 py-2.5">
			<div class="flex min-w-0 flex-col gap-1">
				<div class="mt-1 text-sm font-semibold text-ink-gray-9">Bob AI</div>
				<!-- min-h holds the row while the title is still blank -->
				<div class="min-h-4 truncate text-p-xs leading-4 text-ink-gray-5">
					{{ isSubmitting ? currentActivity : currentSessionTitle }}
				</div>
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
				<Tooltip text="AI settings">
					<Button
						variant="ghost"
						size="sm"
						icon="lucide-settings-2"
						@click="builderStore.openBuilderSettings('global_ai')" />
				</Tooltip>
			</div>
		</div>

		<!-- one element spans both waits (setup verdict + session load) so the
		     shimmer never blinks; the delayed fade keeps fast loads flash-free -->
		<div
			v-if="!builderStore.isAIStateKnown || (isLoadingSession && !messages.length)"
			class="flex flex-1 items-center justify-center pb-40">
			<span class="bob-pill-in" style="animation-delay: 300ms">
				<span class="animate-shine text-p-xs">Loading</span>
			</span>
		</div>

		<!-- pb offsets the centring so it sits in the upper third: dead centre of a
		     full-height panel leaves it stranded low with nothing beneath it. -->
		<div
			v-else-if="!builderStore.isAIEnabled"
			class="flex flex-1 flex-col items-center justify-center gap-4 p-6 pb-40">
			<span class="bob-hero-orb">
				<BobOrb class="bob-orb-aura" />
				<SparklesIcon class="bob-orb-spark relative z-10 size-7 text-ink-gray-8" />
			</span>
			<div class="flex flex-col items-center gap-1 text-center">
				<p class="text-sm font-medium text-ink-gray-8">Build pages by describing them</p>
				<p class="text-p-xs text-ink-gray-5">
					Connect a model first. Takes a minute if you already have an API key.
				</p>
			</div>
			<Button variant="solid" size="sm" @click="builderStore.openBuilderSettings('global_ai')">
				Set up AI
			</Button>
		</div>

		<template v-else>
			<!-- <div class="border-b border-outline-gray-1 px-4 py-3">
				<OptionToggle v-model="scope" :options="scopeOptions" />
			</div> -->

			<div ref="messageContainer" class="no-scrollbar flex-1 space-y-4 overflow-y-auto px-4 py-4">
				<div v-if="!messages.length" class="flex h-full flex-col items-center justify-center gap-5 px-4 pb-8">
					<div class="flex flex-col items-center gap-2.5">
						<span class="bob-hero-orb">
							<BobOrb class="bob-orb-aura" />
							<SparklesIcon class="bob-orb-spark relative z-10 size-7 text-ink-gray-8" />
						</span>
						<p class="text-sm font-medium text-ink-gray-8">
							{{ pageHasContent ? "What should we change?" : "Tell me what you're building" }}
						</p>
						<p class="text-p-xs text-ink-gray-5">Try one of these, or type your own below</p>
					</div>
					<div class="flex w-full flex-col gap-2">
						<Button
							v-for="(suggestion, i) in promptSuggestions"
							:key="suggestion.label"
							class="bob-pill-in"
							:style="{ animationDelay: `${i * 70}ms` }"
							variant="subtle"
							size="xs"
							@click="useSuggestion(suggestion)">
							{{ suggestion.label }}
						</Button>
					</div>
				</div>
				<div
					v-for="message in visibleMessages"
					:key="message.id"
					class="flex flex-col"
					:class="message.role === 'user' ? 'items-end' : 'items-start'">
					<div
						class="w-fit text-p-sm text-ink-gray-8"
						:class="
							message.role === 'user'
								? 'max-w-[88%] rounded-md border px-3 py-2 shadow-sm'
								: 'w-full max-w-full'
						">
						<!-- ui-card messages persist the full card as text (for model replay);
						     the bubble shows only the short lead-in — the card renders the rest -->
						<template v-if="message.role === 'assistant'">
							<!-- What Bob thought, ran and said on the way to this answer. Steps
							     carry their own running state; the row below covers the stretches
							     where no step is on the clock. -->
							<AITurnTimeline
								v-if="message.metadata?.steps?.length"
								:steps="message.metadata.steps"
								:working="stillWorking(message) && !assistantText(message)"
								class="mb-2" />
							<div
								v-if="assistantText(message)"
								class="ai-prose prose prose-sm max-w-none break-words text-p-sm"
								v-html="renderMarkdown(assistantText(message))" />
							<!-- Turn running, nothing on the clock. Between rounds the shimmer is
							     the timeline's own tail row (same geometry as the steps, so the
							     next step replaces it in place, no layout shift); this standalone
							     line covers only what the timeline can't — the answer already
							     streaming (it sits below the reply as the turn's status, never the
							     reply shimmering while it's read) or no steps yet. -->
							<!-- mt-1 only under a streamed reply: standing alone it must sit exactly
							     where the timeline's first row lands, or the label jumps 4px the
							     moment "Working" becomes "Thinking". -->
							<div
								v-if="stillWorking(message) && (!!assistantText(message) || !message.metadata?.steps?.length)"
								class="animate-shine w-fit text-p-xs text-ink-gray-5"
								:class="assistantText(message) && 'mt-1'">
								Working
							</div>
						</template>
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
						<!-- Sensitive action — needs the user's OK. Calm neutral surface with a
						     small amber eyebrow: the QUESTION is the content, and it appears once
						     (the model-facing summary text is suppressed above), so the card
						     reads as a decision, not an alarm. -->
						<div
							v-if="message.metadata?.status === 'pending_action'"
							class="mt-2 w-full rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
							<p class="text-p-xs font-medium text-ink-amber-8">Needs your OK</p>
							<p class="mt-1 text-p-sm leading-snug text-ink-gray-8">
								{{ pendingPreview(message.metadata) }}
							</p>
							<div v-if="message.id === lastMessageId" class="mt-3 flex gap-2">
								<Button
									variant="solid"
									size="sm"
									:loading="confirmingAction"
									@click="confirmPendingAction(message, 'apply')">
									{{ applyLabel(message.metadata?.kind) }}
								</Button>
								<Button
									variant="subtle"
									size="sm"
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
							:answered-with="replyTo(message)"
							:lead="message.metadata.text"
							@submit="selectOption" />
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
				<!-- Canvas selection alone sends nothing; attaching is the explicit act
				     that scopes the request. -->
				<div
					v-if="attachedBlocks.length || attachableBlocks.length"
					class="mb-2 flex flex-wrap items-center gap-1.5">
					<span v-if="attachedBlocks.length" class="text-xs text-ink-gray-5">Context:</span>
					<span
						v-for="block in attachedBlocks"
						:key="block.id"
						class="inline-flex items-center gap-1 rounded bg-surface-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-7">
						<span class="lucide-square-dashed h-3 w-3 shrink-0 text-ink-gray-5" />
						<span class="block max-w-[8rem] truncate">{{ block.label }}</span>
						<button
							type="button"
							class="ml-0.5 flex items-center text-ink-gray-4 hover:text-ink-red-7"
							title="Remove from context"
							@click="chat.detachBlock(block.id)">
							<span class="lucide-x h-3 w-3" />
						</button>
					</span>
					<button
						v-if="attachableBlocks.length"
						type="button"
						class="inline-flex items-center gap-1 rounded border border-dashed border-outline-gray-2 px-1.5 py-0.5 text-xs text-ink-gray-5 hover:border-outline-gray-3 hover:text-ink-gray-7"
						@click="chat.attachSelection()">
						<span class="lucide-plus h-3 w-3" />
						<span class="block max-w-[10rem] truncate">
							{{
								attachableBlocks.length === 1
									? attachableBlocks[0].getBlockDescription()
									: `${attachableBlocks.length} selected blocks`
							}}
						</span>
					</button>
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
				<!-- Say it before a prompt is typed, not after the send fails on the server. -->
				<div
					v-if="selectedModelUnusable"
					class="mb-2 flex items-center gap-2 rounded-md bg-surface-amber-1 px-2.5 py-1.5 text-p-xs text-ink-amber-7">
					<span class="lucide-key-round size-3.5 shrink-0" />
					<span class="flex-1">{{ modelLabel }} has no API key.</span>
					<button
						class="shrink-0 font-medium underline underline-offset-2"
						@click="builderStore.openBuilderSettings('global_ai')">
						Add one
					</button>
				</div>
				<div
					class="relative"
					@paste.stop="handlePaste"
					@dragover.prevent="isDragging = isVisionModel ? true : isDragging"
					@dragleave="isDragging = false"
					@drop.prevent="handleDrop">
					<!-- Grows with the prompt (see autoGrow) between min-h and max-h; past
					     that it scrolls. The suggestion pills prefill a paragraph, so a
					     fixed four rows meant the brief you're about to send was mostly
					     out of sight. -->
					<textarea
						ref="promptInput"
						v-model="prompt"
						rows="1"
						class="no-scrollbar block max-h-60 min-h-20 w-full resize-none rounded border border-[--surface-gray-2] bg-surface-gray-2 px-2 py-1.5 text-p-sm text-ink-gray-8 placeholder-ink-gray-4 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-3 focus:border-outline-gray-4 focus:bg-surface-base focus:shadow-sm focus:ring-0 focus-visible:ring-2 focus-visible:ring-outline-gray-3 disabled:cursor-not-allowed disabled:bg-surface-gray-1 disabled:text-ink-gray-5"
						:disabled="isSubmitting"
						placeholder="Ask to create or edit this page…"
						@keydown.meta.enter="submitPrompt"
						@keydown.ctrl.enter="submitPrompt" />
					<Transition name="fade">
						<!-- inset-0 covers the wrapper, so the textarea has to fill it exactly:
						     as an inline-block it left a few px of line-box gap underneath and
						     the target hung past the field. Same radius as the field, too. -->
						<div
							v-if="isDragging"
							class="pointer-events-none absolute inset-0 flex items-center justify-center rounded border-2 border-dashed border-outline-blue-3 bg-surface-blue-1/60">
							<div class="flex items-center gap-1.5 text-xs font-medium text-ink-blue-4">
								<span class="lucide-image h-3.5 w-3.5" />
								Drop image to attach
							</div>
						</div>
					</Transition>
					<!-- Only on an empty box: it sits over the textarea, so once there's a
					     prompt long enough to reach it the hint lands on the user's words. -->
					<span
						v-if="isVisionModel && !prompt && !imagePreviewUrl && !isDragging"
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
						<Tooltip text="Improve prompt" placement="top">
							<button
								class="flex size-7 items-center justify-center rounded text-ink-gray-5 transition-colors hover:bg-surface-gray-2 hover:text-ink-gray-8 disabled:cursor-not-allowed disabled:opacity-40"
								:disabled="!prompt.trim() || isImprovingPrompt || isSubmitting"
								@click="chat.improvePrompt">
								<span v-if="isImprovingPrompt" class="lucide-loader-circle size-3.5 animate-spin" />
								<span v-else class="lucide-wand-sparkles size-3.5" />
							</button>
						</Tooltip>
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
import AITurnTimeline from "@/components/ai/AITurnTimeline.vue";
import AIUISpec from "@/components/ai/AIUISpec.vue";
import BobOrb from "@/components/ai/BobOrb.vue";
import { AIChatController, type ChatMessage } from "@/components/AIChatController";
import AIDebugPanel from "@/components/AIDebugPanel.vue";
import Dialog from "@/components/Controls/Dialog.vue";
import SparklesIcon from "@/components/Icons/Sparkles.vue";
import { cardAnswers } from "@/components/ai/cardAnswers";
import { renderMarkdown } from "@/components/ai/markdown";
import type { AITurnStep } from "@/components/ai/types";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import { Button, Dropdown, Popover, Tooltip } from "frappe-ui";
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";

const chat = new AIChatController();

const { prompt, isSubmitting, isCancelling, messages, modelLabel, modelOptions, canSubmit } = chat;
const { isImprovingPrompt } = chat;
const { selectedModelUnusable } = chat;
const { progressMessage } = chat;
const currentActivity = computed(() => progressMessage.value || "Thinking…");
const { revertTurn, selectOption } = chat;
const { sessions, sessionId, switchSession, newSession, deleteSession, isLoadingSession } = chat;

const currentSessionTitle = computed(() => {
	// blank until loaded, not "New chat" flipping to the real title
	if (!sessionId.value || !sessions.value.length) return "";
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
	// Delete sits in its own group so it reads as an action on the current chat
	// rather than a fifth chat to switch to — frappe-ui draws the divider.
	return [
		{
			group: "Chats",
			hideLabel: true,
			options: sessions.value.map((s) => ({
				label: truncateTitle(s.title || "New chat"),
				icon: s.name === sessionId.value ? "lucide-check" : "lucide-message-circle",
				onClick: () => switchSession(s.name),
			})),
		},
		{
			group: "Manage",
			hideLabel: true,
			// theme belongs on the item — a group-level one isn't inherited.
			options: [
				{
					label: "Delete current chat",
					icon: "lucide-trash-2",
					theme: "red",
					onClick: deleteSession,
				},
			],
		},
	];
});
const { selectBlockById, openScriptByName } = chat;
const { attachedBlocks, attachableBlocks } = chat;
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
/** The fields as the user would name them ("Name, Email, Message") — the card
 * must say what gets stored, not count fields in engineering vocabulary. */
function fieldNames(fields: any[]): string {
	return (fields || [])
		.map((f) => f?.label || f?.fieldname)
		.filter(Boolean)
		.join(", ");
}

function pendingPreview(m: Record<string, any>): string {
	const p = m.payload || {};
	const fields = fieldNames(p.fields);
	switch (m.kind) {
		case "create_doctype":
			return `Create “${p.name}” to store this page's data${fields ? ` (${fields})` : ""}.`;
		case "connect_form":
			return `Save this form's submissions as “${p.doctype_name}” records${fields ? ` (${fields})` : ""}.`;
		case "seed_sample_data": {
			const n = (p.rows || []).length;
			return `Add ${n} sample ${n === 1 ? "record" : "records"} to “${p.doctype}”.`;
		}
		case "global_settings":
			return `Update site-wide code (${Object.keys(p).join(", ")}). This loads on every page.`;
		case "home_page":
			return `Make “/${String(p.route || "").replace(/^\//, "")}” the site's home page.`;
		default:
			return "Confirm this change?";
	}
}

/** The apply button names the action it performs; a bare "Apply" makes the user
 * re-read the card to know what they're agreeing to. */
const APPLY_LABELS: Record<string, string> = {
	create_doctype: "Create it",
	connect_form: "Connect form",
	seed_sample_data: "Add records",
	home_page: "Set home page",
	global_settings: "Apply",
};
const applyLabel = (kind?: string) => APPLY_LABELS[kind || ""] || "Apply";
const builderStore = useBuilderStore();
const canvasStore = useCanvasStore();

const lastMessageId = computed(() => messages.value.at(-1)?.id ?? null);

/** The answer itself, without the timeline that led to it. A card message persists
 * its whole card as text so the model sees it on replay — the chat shows only the
 * lead-in and lets AIUISpec draw the rest. A pending-action message's content is
 * the model-facing summary, and the card already asks the question in human terms;
 * rendering both put the same ask on screen twice, once in jargon. */
function assistantText(message: ChatMessage): string {
	if (message.metadata?.status === "pending_action") return "";
	return message.metadata?.status === "ui" ? (message.metadata?.text ?? message.content) : message.content;
}

/** Whether the turn is running with nothing to show for it. Every step it finishes
 * (a thought, a tool) states its own time and then goes quiet, so the long stretches
 * (a tool call whose arguments are still streaming, the wait for the next round)
 * left the chat looking like it had died mid-turn. */
function stillWorking(message: ChatMessage): boolean {
	// Only the turn this tab is running: a turn that died mid-flight is persisted
	// as "running" too, and on reload that would shimmer forever.
	if (!isSubmitting.value || message.id !== lastMessageId.value) return false;
	if (message.metadata?.status !== "running") return false;
	return !(message.metadata.steps || []).some((step: AITurnStep) => step.status === "running");
}

/** The reply a card was answered with: the user message right after it. That
 * message IS the answer (the card submits as an ordinary chat reply), so an
 * answered card can show what was chosen without storing it twice. */
function replyTo(message: ChatMessage): string | undefined {
	const next = messages.value[messages.value.findIndex((m) => m.id === message.id) + 1];
	return next?.role === "user" ? next.content : undefined;
}

/** A card that reads back every answer makes the bubble under it a second copy
 * of itself, so the card is the record and the reply drops out of the chat.
 * Only when the card actually paired them: a reply it can't show (an action
 * button, an unlabelled question) is left to speak for itself. */
const visibleMessages = computed(() =>
	messages.value.filter((message, i) => {
		if (message.role !== "user") return true;
		const card = messages.value[i - 1]?.metadata;
		if (card?.status !== "ui" || !card?.ui?.length) return true;
		return !cardAnswers(card.ui, message.content, card.text).length;
	}),
);

// --- Empty-state suggestions -------------------------------------------------
// Fresh page → describe the site to build; page with content → describe a change.
// Each pill shows a short `label` but prefills a rich `prompt` — a complete brief
// (name, vibe, sections, emphasis) so the agent can proceed with the fewest
// follow-up questions. It's an editable starting point, not a command.
// A wide, characterful pool sampled 3-at-a-time so the panel feels fresh.
type Suggestion = { label: string; prompt: string };
const pageHasContent = computed(() => (canvasStore.activeCanvas?.getRootBlock()?.children?.length ?? 0) > 0);
const BUILD_POOL: Suggestion[] = [
	{
		label: "A wood-fired pizzeria in Goa",
		prompt:
			"Build a website for Forno, a wood-fired pizzeria in Anjuna, Goa. Warm, rustic-modern feel with big appetizing food photography and a cozy dark-terracotta palette. Sections: a hero with our story, the menu (wood-fired pizzas, small plates, natural wines), a photo gallery, and a visit section with hours and location.",
	},
	{
		label: "Moody portfolio for a photographer",
		prompt:
			"Build a portfolio for Aria Sen, a portrait and editorial photographer. Dark, cinematic, image-first design where the photos dominate. Sections: a full-bleed hero image, a gallery of selected work, a short about/bio, a client list, and a contact/booking section.",
	},
	{
		label: "Waitlist page for an AI app",
		prompt:
			"Build a launch and waitlist page for Nimbus, an AI note-taking app. Clean and modern with a confident gradient accent. Sections: a punchy hero with the value prop and an email waitlist form, three key features, a short 'how it works', and social proof.",
	},
	{
		label: "Menu & story for a ramen bar",
		prompt:
			"Build a website for Slurp, a ramen bar in Bandra, Mumbai. Bold, appetizing, a little playful. Sections: a hero, the ramen menu with descriptions and prices, our origin story, a gallery, and hours and location.",
	},
	{
		label: "A vintage record store",
		prompt:
			"Build a website for Groove Vault, a vintage vinyl record store. Retro, textured, warm analog vibe. Sections: a hero, featured new arrivals, the genres we stock, our story, in-store events, and how to find us.",
	},
	{
		label: "Landing page for a yoga studio",
		prompt:
			"Build a landing page for Stillpoint, a boutique yoga studio. Calm, airy, minimal with soft natural tones and gentle motion. Sections: a hero, class types and schedule, the teachers, a membership/pricing section, and a book-a-first-class CTA.",
	},
	{
		label: "A bold skincare brand",
		prompt:
			"Build a product site for Lumen, a clean skincare brand. Bold, premium, editorial with big product shots. Sections: a hero, the hero product with ingredients and benefits, results, reviews, and a shop/buy CTA.",
	},
	{
		label: "Personal site for a designer",
		prompt:
			"Build a personal site for Maya Rao, a product designer. Confident, minimal, type-driven. Sections: a short intro hero, selected case studies, an about section, and contact links (email, LinkedIn, resume).",
	},
	{
		label: "A craft coffee roaster",
		prompt:
			"Build a website for Ember & Oak, a craft coffee roaster. Warm, artisanal, rich browns and texture. Sections: a hero, our roasts with tasting notes, the roasting story, wholesale info, and where to buy or visit.",
	},
	{
		label: "Event page for a design meetup",
		prompt:
			"Build an event page for Design Jam, a monthly design meetup in Pune. Energetic, modern, poster-like. Sections: a hero with date, venue and RSVP, the speaker lineup, the schedule, past-event highlights, and sponsors.",
	},
];
const EDIT_POOL: Suggestion[] = [
	{
		label: "Add a testimonials section",
		prompt:
			"Add a testimonials section with three or four short customer quotes, each with a name and role, styled to match the rest of the page.",
	},
	{
		label: "Make the hero more dramatic",
		prompt:
			"Make the hero more dramatic: a larger headline, stronger contrast, a full-bleed background image or bold color, and a clear primary call-to-action.",
	},
	{
		label: "Switch to a dark theme",
		prompt:
			"Rework the whole page in a cohesive dark theme, keeping the layout but adjusting backgrounds, text, and accents for good contrast.",
	},
	{
		label: "Add a pricing section",
		prompt:
			"Add a pricing section with three tiers (name, price, feature list, and a CTA button each), styled to match the page.",
	},
	{
		label: "Add scroll animations",
		prompt:
			"Add tasteful scroll animations: staggered fade-and-rise reveals on each section as it enters the viewport, subtle and smooth.",
	},
	{
		label: "Tighten the spacing everywhere",
		prompt:
			"Tighten the spacing across the page: reduce oversized gaps, align section padding to a consistent rhythm, and improve the vertical flow.",
	},
	{
		label: "Add a sticky header with nav",
		prompt:
			"Add a sticky header with the name or logo on the left and nav links to each section on the right, gaining a subtle background on scroll.",
	},
	{
		label: "Make it feel more premium",
		prompt:
			"Make the page feel more premium: refine the typography and spacing, add depth with subtle shadows and borders, and elevate the color and imagery treatment.",
	},
];
function sample3(pool: Suggestion[]): Suggestion[] {
	return [...pool].sort(() => Math.random() - 0.5).slice(0, 3);
}
// Picked once per mount (a computed would reshuffle on every reactive read).
const buildPicks = sample3(BUILD_POOL);
const editPicks = sample3(EDIT_POOL);
const promptSuggestions = computed(() => (pageHasContent.value ? editPicks : buildPicks));
const promptInput = ref<HTMLTextAreaElement | null>(null);
function useSuggestion(suggestion: Suggestion) {
	prompt.value = suggestion.prompt;
	promptInput.value?.focus();
}

/** Size the box to its content. Reset to auto first — scrollHeight only ever
 * grows while an explicit height is set, so without it the box could never
 * shrink back after the prompt is sent or cleared. The min/max come from the
 * element's own classes, so the clamp lives in one place. */
function autoGrow() {
	const el = promptInput.value;
	if (!el) return;
	el.style.height = "auto";
	el.style.height = `${el.scrollHeight}px`;
}
watch(prompt, () => nextTick(autoGrow), { immediate: true });

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
		(debug.argsRepaired ?? 0) > 0 ||
			(debug.toolFailures?.length ?? 0) > 0 ||
			(debug.finishReasons || []).includes("length") ||
			debug.stopReason === "max_rounds",
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

const submitPrompt = () => {
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

onMounted(() => {
	chat.mount();
	// A key on a provider is invisible to the client, so ask the server whether AI
	// is actually usable rather than inferring it from Builder Settings alone.
	builderStore.refreshAIState();
});

// the chat usually loads behind the closed tab, where the scroll can't land
watch(
	() => builderStore.leftPanelActiveTab,
	(tab) => {
		if (tab === "Chat") chat.flushPendingScroll();
	},
);

// Providers and models are configured in Settings, so the picker is stale the
// moment that dialog closes. Refetch then rather than making every screen in
// there remember to signal this one.
watch(
	() => builderStore.showSettingsDialog,
	(open, wasOpen) => {
		if (wasOpen && !open) {
			chat.loadModels();
			builderStore.refreshAIState();
		}
	},
);
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
	/* Code blocks: typography's pre defaults are fixed light-theme colors, so on
	 * the dark panel a route tree rendered as barely-visible dark-on-dark. Pin
	 * BOTH sides of the pair to theme-adaptive tokens (they flip together). */
	--tw-prose-pre-code: var(--ink-gray-8);
	--tw-prose-pre-bg: var(--surface-gray-2);
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
/* The travelling band has to move AWAY from the page, not toward it. On dark
 * that means brightening to near-white, which reads as a glint. Light mode ran
 * the same direction — mid-grey darkening to near-black — so the text only got
 * inkier for a moment and the motion didn't register. There it needs the
 * opposite: dark text with a pale sheen passing over it. */
.animate-shine {
	--shine-base: var(--ink-gray-8);
	--shine-peak: var(--ink-gray-4);
	background: linear-gradient(120deg, var(--shine-base) 20%, var(--shine-peak) 50%, var(--shine-base) 80%);
	background-size: 200% auto;
	-webkit-background-clip: text;
	background-clip: text;
	-webkit-text-fill-color: transparent;
	animation: shine 2.5s linear infinite;
}
[data-theme="dark"] .animate-shine {
	--shine-base: var(--ink-gray-6);
	--shine-peak: var(--ink-gray-9);
}

/* Empty-state hero: a living aurora of drifting color blobs behind the sparkle.
 * Each blob only animates transform (GPU-composited) under a single static blur,
 * so the motion stays silky. Prime-ish, mismatched durations keep it organic —
 * the loop never visibly repeats. */
.bob-hero-orb {
	position: relative;
	display: grid;
	place-items: center;
	width: 76px;
	height: 76px;
	isolation: isolate;
}
/* Soft outer bloom that gently breathes */
.bob-hero-orb::after {
	content: "";
	position: absolute;
	inset: 4px;
	border-radius: 999px;
	background: radial-gradient(circle, rgb(139 92 246 / 0.28), transparent 70%);
	filter: blur(7px);
	z-index: 0;
	animation: bob-orb-bloom 5s ease-in-out infinite;
}
@keyframes bob-orb-bloom {
	0%,
	100% {
		opacity: 0.55;
		transform: scale(0.9);
	}
	50% {
		opacity: 1;
		transform: scale(1.08);
	}
}

/* The shader canvas, clipped to a soft disc. A light blur melts the pixel grid
 * into the surrounding bloom so the edge reads as glow, not a hard circle. */
.bob-orb-aura {
	position: absolute;
	inset: -6%;
	z-index: 1;
	border-radius: 999px;
	overflow: hidden;
	filter: blur(4px) saturate(1.15);
}

/* The sparkle sits above the aura with a soft glow and a gentle twinkle */
.bob-orb-spark {
	filter: drop-shadow(0 0 6px rgb(196 181 253 / 0.7));
	animation: bob-twinkle 3.4s ease-in-out infinite;
}
@keyframes bob-twinkle {
	0%,
	100% {
		opacity: 0.9;
		transform: scale(1) rotate(0deg);
	}
	50% {
		opacity: 1;
		transform: scale(1.08) rotate(4deg);
	}
}

/* Suggestion pills fade-and-rise in, staggered */
.bob-pill-in {
	animation: bob-pill-in 0.4s ease both;
}
@keyframes bob-pill-in {
	from {
		opacity: 0;
		transform: translateY(6px);
	}
	to {
		opacity: 1;
		transform: translateY(0);
	}
}

@media (prefers-reduced-motion: reduce) {
	.bob-hero-orb::after,
	.bob-blob,
	.bob-orb-spark,
	.bob-pill-in,
	.animate-shine {
		animation: none;
	}
}
</style>
