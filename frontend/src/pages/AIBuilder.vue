<template>
	<div class="bg-surface-white flex h-screen text-ink-gray-8">
		<!-- sessions sidebar -->
		<aside class="flex w-60 shrink-0 flex-col border-r border-outline-gray-2">
			<div class="flex items-center justify-between px-3 py-3">
				<Button variant="ghost" icon-left="lucide-arrow-left" label="Dashboard" @click="goHome" />
				<Button variant="ghost" icon="lucide-plus" @click="newChat" />
			</div>
			<div class="flex-1 overflow-auto px-2 pb-3">
				<div
					v-for="s in chat.sessions.value"
					:key="s.name"
					class="group mb-0.5 flex w-full cursor-pointer items-center gap-1 rounded-md py-1 pl-2.5 pr-1 text-sm leading-snug"
					:class="
						s.name === chat.sessionId.value
							? 'bg-surface-gray-3 text-ink-gray-9'
							: 'text-ink-gray-6 hover:bg-surface-gray-2'
					"
					@click="openSession(s.name)">
					<EditableSpan
						v-model="s.title"
						:editable="renamingSession === s.name"
						:onChange="
							async (newTitle: string) => {
								await chat.renameSession(s.name, newTitle);
								renamingSession = '';
							}
						"
						class="min-w-0 flex-1 truncate py-1"
						@blur="renamingSession = ''">
						{{ s.title || "New chat" }}
					</EditableSpan>
					<!-- The slot content IS the trigger (reka-ui as-child) — no open() call;
					     @click.stop only keeps the row's openSession from firing. -->
					<Dropdown
						side="right"
						align="start"
						:options="[
							{ label: 'Rename', icon: 'lucide-edit', onClick: () => (renamingSession = s.name) },
							{ label: 'Delete', icon: 'lucide-trash', onClick: () => removeSession(s.name) },
						]">
						<Button
							icon="lucide-more-horizontal"
							size="sm"
							variant="ghost"
							class="opacity-0 group-hover:opacity-100"
							@click.stop />
					</Dropdown>
				</div>
			</div>
		</aside>

		<!-- conversation -->
		<main class="flex min-w-0 flex-1 flex-col">
			<div ref="scrollEl" class="flex-1 overflow-auto">
				<div class="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-8">
					<div v-if="!chat.messages.value.length" class="pt-16 text-center">
						<h1 class="text-xl font-semibold text-ink-gray-9">What do you want to build?</h1>
						<p class="mt-1.5 text-p-base text-ink-gray-5">
							A whole site, a page, or a quick change - just ask.
						</p>
					</div>
					<AgentMessage
						v-for="m in chat.messages.value"
						:key="m.id"
						:message="m"
						:batch="m.batchId ? chat.batches.value[m.batchId] : null"
						:publishing="false"
						@select-option="chat.selectOption"
						@approve-plan="chat.approvePlan"
						@confirm="chat.confirmAction"
						@revert="chat.revertTurn"
						@publish="chat.publishBatch"
						@cancel-batch="chat.cancelBatch" />
				</div>
			</div>

			<!-- composer -->
			<div class="border-t border-outline-gray-2 px-6 py-4">
				<div class="relative mx-auto max-w-2xl">
					<!-- inline @page mention list (keyboard-navigable). Positioned above the
					     composer; the "@…" stays inline in the text as a reference. -->
					<div
						v-if="mentionOpen && filteredPages.length"
						class="bg-surface-white absolute bottom-full left-0 mb-2 max-h-60 w-80 overflow-auto rounded-lg border border-outline-gray-2 py-1 shadow-lg">
						<button
							v-for="(p, i) in filteredPages"
							:key="p.name"
							class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-sm"
							:class="
								i === mentionIndex
									? 'bg-surface-gray-3 text-ink-gray-9'
									: 'text-ink-gray-8 hover:bg-surface-gray-2'
							"
							@mousemove="mentionIndex = i"
							@mousedown.prevent="selectMention(p)">
							<FeatherIcon name="file" class="size-3.5 shrink-0 text-ink-gray-4" />
							<span class="min-w-0 flex-1 truncate">{{ p.page_title || p.name }}</span>
							<span class="shrink-0 font-mono text-xs text-ink-gray-4">
								/{{ (p.route || "").replace(/^\//, "") }}
							</span>
						</button>
					</div>

					<div
						class="ai-composer bg-surface-white rounded-xl border border-outline-gray-2 px-4 py-3"
						:class="{ 'border-outline-gray-4': isDragging }"
						@dragover.prevent="isDragging = true"
						@dragleave="isDragging = false"
						@drop.prevent="onDrop">
						<!-- attached image (vision) -->
						<div v-if="chat.imageData.value" class="mb-1.5 flex">
							<div class="relative">
								<img
									:src="chat.imageData.value"
									class="h-14 rounded-md border border-outline-gray-2 object-cover"
									alt="Attached image" />
								<Button
									icon="lucide-x"
									size="xs"
									variant="solid"
									class="absolute -right-2 -top-2"
									@click="chat.clearImage" />
							</div>
						</div>
						<textarea
							ref="inputEl"
							v-model="chat.prompt.value"
							rows="2"
							placeholder="Ask Builder AI…  (type @ to reference a page)"
							class="ai-input block max-h-52 w-full resize-none border-0 bg-transparent p-0 text-p-base leading-relaxed text-ink-gray-9 placeholder:text-ink-gray-4"
							@input="onInput"
							@keydown="onKeydown"
							@paste="onPaste" />
						<div class="mt-2 flex items-center gap-2">
							<Dropdown :options="modelOptions" side="top" align="start">
								<Button variant="ghost" :label="modelLabel" icon-right="lucide-chevron-down" />
							</Dropdown>
							<input ref="fileInput" type="file" accept="image/*" class="hidden" @change="onFilePick" />
							<span class="flex-1"></span>
							<Button v-if="chat.sending.value" variant="subtle" icon="lucide-square" @click="chat.cancel" />
							<Button
								v-else
								variant="solid"
								icon="lucide-arrow-up"
								:disabled="!chat.canSubmit.value"
								@click="onSend" />
						</div>
					</div>
				</div>
			</div>
		</main>
	</div>
</template>

<script setup lang="ts">
import AgentMessage from "@/components/ai-builder/AgentMessage.vue";
import { useAgentChat } from "@/components/ai-builder/useAgentChat";
import EditableSpan from "@/components/EditableSpan.vue";
import router from "@/router";
import { Button, createResource, Dropdown, FeatherIcon } from "frappe-ui";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

interface PageRef {
	name: string;
	page_title?: string;
	route?: string;
}
interface Mention {
	token: string;
	name: string;
	title: string;
	route: string;
}

const route = useRoute();
const chat = useAgentChat();
const inputEl = ref<HTMLTextAreaElement | null>(null);
const scrollEl = ref<HTMLElement | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);
const isDragging = ref(false);
const renamingSession = ref("");

// Inline @page references. The "@Title" stays in the prompt text; the resolved pages
// ride along to the backend as context so the agent knows which page each refers to.
const allPages = ref<PageRef[]>([]);
const mentionOpen = ref(false);
const mentionQuery = ref("");
const mentionIndex = ref(0);
const mentions = ref<Mention[]>([]);

const routeSessionId = computed(() => (route.params.sessionId as string) || "");
const modelLabel = computed(
	() => chat.models.value.find((m) => m.name === chat.selectedModel.value)?.label || "Model",
);
const modelOptions = computed(() =>
	chat.models.value.map((m) => ({ label: m.label, onClick: () => (chat.selectedModel.value = m.name) })),
);
const filteredPages = computed(() => {
	const q = mentionQuery.value.trim().toLowerCase();
	return allPages.value
		.filter((p) => {
			if (!q) return true;
			return (p.page_title || p.name).toLowerCase().includes(q) || (p.route || "").toLowerCase().includes(q);
		})
		.slice(0, 8);
});

function resize() {
	const t = inputEl.value;
	if (!t) return;
	t.style.height = "auto";
	t.style.height = `${Math.min(t.scrollHeight, 208)}px`;
}

function onInput() {
	resize();
	detectMention();
}

/** Open the mention list on a fresh "@" (and keep it open while typing the query
 * right after it). The "@…" is never stripped — it stays inline in the prompt. */
function detectMention() {
	const el = inputEl.value;
	const caret = el?.selectionStart ?? chat.prompt.value.length;
	const m = chat.prompt.value.slice(0, caret).match(/@([^@\n]*)$/);
	if (m && (m[1] === "" || mentionOpen.value)) {
		mentionOpen.value = true;
		mentionQuery.value = m[1];
		mentionIndex.value = 0;
	} else {
		mentionOpen.value = false;
	}
}

function onKeydown(e: KeyboardEvent) {
	const list = filteredPages.value;
	if (mentionOpen.value && list.length) {
		if (e.key === "ArrowDown") {
			e.preventDefault();
			mentionIndex.value = (mentionIndex.value + 1) % list.length;
			return;
		}
		if (e.key === "ArrowUp") {
			e.preventDefault();
			mentionIndex.value = (mentionIndex.value - 1 + list.length) % list.length;
			return;
		}
		if (e.key === "Enter" || e.key === "Tab") {
			e.preventDefault();
			selectMention(list[mentionIndex.value]);
			return;
		}
		if (e.key === "Escape") {
			e.preventDefault();
			mentionOpen.value = false;
			return;
		}
	}
	if (e.key === "Enter" && !e.shiftKey) {
		e.preventDefault();
		onSend();
	}
}

/** A stable, UNIQUE token for the inline reference. Titles can collide (many "My Page"),
 * so when a title isn't unique we disambiguate with the route — otherwise the backend
 * couldn't tell which page "@My Page" meant. */
function tokenFor(p: PageRef): string {
	const title = p.page_title || p.name;
	const dup = allPages.value.filter((x) => (x.page_title || x.name) === title).length > 1;
	return dup && p.route ? `@${title} (/${p.route.replace(/^\//, "")})` : `@${title}`;
}

function selectMention(p: PageRef) {
	const el = inputEl.value;
	const caret = el?.selectionStart ?? chat.prompt.value.length;
	const before = chat.prompt.value.slice(0, caret).replace(/@([^@\n]*)$/, "");
	const after = chat.prompt.value.slice(caret);
	const title = p.page_title || p.name;
	const token = tokenFor(p);
	chat.prompt.value = `${before}${token} ${after}`;
	if (!mentions.value.some((m) => m.name === p.name)) {
		mentions.value.push({ token, name: p.name, title, route: p.route || "" });
	}
	mentionOpen.value = false;
	mentionQuery.value = "";
	nextTick(() => {
		const pos = (before + token + " ").length;
		el?.focus();
		el?.setSelectionRange(pos, pos);
		resize();
	});
}

function onSend() {
	if (!chat.canSubmit.value) return;
	// Only pass references still present in the text (the user may have deleted one).
	const refs = mentions.value
		.filter((m) => chat.prompt.value.includes(m.token))
		.map((m) => ({ name: m.name, title: m.title, route: m.route, token: m.token }));
	chat.send(refs);
	mentions.value = [];
	nextTick(resize);
}

async function loadPages() {
	try {
		allPages.value = await createResource({
			url: "frappe.client.get_list",
			params: {
				doctype: "Builder Page",
				fields: ["name", "page_title", "route"],
				order_by: "modified desc",
				limit_page_length: 0,
			},
		}).fetch();
	} catch {
		/* ignore */
	}
}

function openSession(id: string) {
	if (id === chat.sessionId.value) return;
	router.push({ name: "ai-builder", params: { sessionId: id } });
}

async function removeSession(id: string) {
	const deleted = await chat.deleteSession(id);
	// Deleting the open chat drops you on a fresh one.
	if (deleted && id === chat.sessionId.value) router.push({ name: "ai-builder-new" });
}

function onFilePick(e: Event) {
	const file = (e.target as HTMLInputElement).files?.[0];
	if (file) chat.attachImageFile(file);
	if (fileInput.value) fileInput.value.value = "";
}

function onDrop(e: DragEvent) {
	isDragging.value = false;
	if (!chat.isVisionModel.value) return;
	const file = e.dataTransfer?.files?.[0];
	if (file) chat.attachImageFile(file);
}

function onPaste(e: ClipboardEvent) {
	if (!chat.isVisionModel.value) return;
	const file = Array.from(e.clipboardData?.items || [])
		.find((i) => i.type.startsWith("image/"))
		?.getAsFile();
	if (file) {
		e.preventDefault();
		chat.attachImageFile(file);
	}
}

async function newChat() {
	// Deactivate the current active session and mint a fresh one, then land on it.
	const res: any = await createResource({ url: "builder.ai.api.new_general_session", method: "POST" }).submit(
		{
			model: chat.selectedModel.value,
		},
	);
	await chat.loadSessions();
	router.push({ name: "ai-builder", params: { sessionId: res.session_id } });
}

function goHome() {
	router.push({ name: "home" });
}

async function boot() {
	chat.messageContainer.value = scrollEl.value;
	await chat.open(routeSessionId.value || undefined);
	nextTick(resize);
}

watch(routeSessionId, () => chat.open(routeSessionId.value || undefined));

onMounted(async () => {
	await chat.loadModels();
	await chat.loadSessions();
	loadPages();
	await boot();
});
onBeforeUnmount(() => chat.teardown());
</script>

<style scoped>
/* Kill the app-global `textarea:focus` blue outline/ring (element+pseudo selector
   out-specifies utility classes), and show the focus affordance on the wrapper. */
.ai-input:focus,
.ai-input:focus-visible {
	outline: none !important;
	box-shadow: none !important;
	border-color: transparent !important;
}
.ai-composer:focus-within {
	border-color: var(--outline-gray-3);
}
</style>
