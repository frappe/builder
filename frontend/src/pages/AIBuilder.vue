<template>
	<div class="bg-surface-white flex h-screen text-ink-gray-8">
		<!-- sessions sidebar -->
		<aside class="flex w-60 shrink-0 flex-col border-r border-outline-gray-2">
			<div class="flex items-center justify-between px-3 py-3">
				<button
					class="flex items-center gap-1.5 text-sm text-ink-gray-6 hover:text-ink-gray-9"
					@click="goHome">
					<FeatherIcon name="arrow-left" class="size-3.5" />
					Dashboard
				</button>
				<Button variant="ghost" size="sm" @click="newChat">
					<template #icon><FeatherIcon name="plus" class="size-4" /></template>
				</Button>
			</div>
			<div class="flex-1 overflow-auto px-2 pb-3">
				<button
					v-for="s in chat.sessions.value"
					:key="s.name"
					class="mb-0.5 block w-full truncate rounded-md px-2.5 py-2 text-left text-xs leading-snug"
					:class="
						s.name === chat.sessionId.value
							? 'bg-surface-gray-3 text-ink-gray-9'
							: 'text-ink-gray-6 hover:bg-surface-gray-2'
					"
					@click="openSession(s.name)">
					{{ s.title || "New chat" }}
				</button>
			</div>
		</aside>

		<!-- conversation -->
		<main class="flex min-w-0 flex-1 flex-col">
			<div ref="scrollEl" class="flex-1 overflow-auto">
				<div class="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-8">
					<div v-if="!chat.messages.value.length" class="pt-16 text-center">
						<h1 class="text-xl font-semibold text-ink-gray-9">What do you want to build?</h1>
						<p class="mt-1.5 text-p-base text-ink-gray-5">
							A whole site, a page, or a quick change — just ask.
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
						@publish="chat.publishBatch" />
				</div>
			</div>

			<!-- composer -->
			<div class="border-t border-outline-gray-2 px-6 py-3">
				<div class="relative mx-auto max-w-2xl">
					<!-- @page mention picker -->
					<div
						v-if="mentionActive && filteredPages.length"
						class="bg-surface-white absolute bottom-full left-0 mb-2 max-h-56 w-72 overflow-auto rounded-lg border border-outline-gray-2 py-1 shadow-lg">
						<button
							v-for="p in filteredPages"
							:key="p.name"
							class="flex w-full items-center gap-2 px-3 py-1.5 text-left text-xs text-ink-gray-8 hover:bg-surface-gray-2"
							@mousedown.prevent="selectPage(p)">
							<FeatherIcon name="file" class="size-3.5 shrink-0 text-ink-gray-4" />
							<span class="min-w-0 flex-1 truncate">{{ p.page_title || p.name }}</span>
							<span class="shrink-0 font-mono text-[10px] text-ink-gray-4">
								/{{ (p.route || "").replace(/^\//, "") }}
							</span>
						</button>
					</div>

					<div class="ai-composer bg-surface-white rounded-xl border border-outline-gray-2 px-3 py-2.5">
						<!-- referenced page chip -->
						<div
							v-if="targetPage"
							class="mb-1.5 inline-flex items-center gap-1.5 rounded-md bg-surface-gray-2 px-2 py-1 text-[11px] text-ink-gray-7">
							<FeatherIcon name="file" class="size-3" />
							<span class="max-w-[180px] truncate">{{ targetPage.title }}</span>
							<button class="text-ink-gray-5 hover:text-ink-gray-8" @click="targetPage = null">
								<FeatherIcon name="x" class="size-3" />
							</button>
						</div>
						<textarea
							ref="inputEl"
							v-model="chat.prompt.value"
							rows="1"
							:placeholder="
								targetPage
									? `Ask to change ${targetPage.title}…`
									: 'Ask Builder AI…  (type @ to reference a page)'
							"
							class="ai-input block max-h-40 w-full resize-none border-0 bg-transparent text-p-sm leading-relaxed text-ink-gray-9 placeholder:text-ink-gray-4"
							@input="onInput"
							@keydown.enter.exact.prevent="onEnter"
							@keydown.esc="mentionActive = false" />
						<div class="mt-1.5 flex items-center gap-2">
							<Dropdown :options="modelOptions" placement="top-start">
								<button class="rounded px-1.5 py-1 text-[11px] text-ink-gray-5 hover:bg-surface-gray-2">
									{{ modelLabel }}
								</button>
							</Dropdown>
							<span class="flex-1"></span>
							<Button v-if="chat.sending.value" variant="subtle" @click="chat.cancel">
								<template #icon><FeatherIcon name="square" class="size-3.5" /></template>
							</Button>
							<Button v-else variant="solid" :disabled="!canSend" @click="onSend">
								<template #icon><FeatherIcon name="arrow-up" class="size-4" /></template>
							</Button>
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
import router from "@/router";
import { Button, createResource, Dropdown, FeatherIcon } from "frappe-ui";
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

interface PageRef {
	name: string;
	page_title?: string;
	route?: string;
}

const route = useRoute();
const chat = useAgentChat();
const inputEl = ref<HTMLTextAreaElement | null>(null);
const scrollEl = ref<HTMLElement | null>(null);

// @page mention state
const allPages = ref<PageRef[]>([]);
const mentionActive = ref(false);
const mentionQuery = ref("");
const targetPage = ref<{ name: string; title: string } | null>(null);

const routeSessionId = computed(() => (route.params.sessionId as string) || "");
const modelLabel = computed(
	() => chat.models.value.find((m) => m.name === chat.selectedModel.value)?.label || "Model",
);
const modelOptions = computed(() =>
	chat.models.value.map((m) => ({ label: m.label, onClick: () => (chat.selectedModel.value = m.name) })),
);
const filteredPages = computed(() => {
	const q = mentionQuery.value.toLowerCase();
	return allPages.value.filter((p) => (p.page_title || p.name).toLowerCase().includes(q)).slice(0, 8);
});
// A referenced page hands off to the editor, so a bare "@Home" with no instruction
// is still sendable; otherwise require text + a model.
const canSend = computed(() => (!!targetPage.value || chat.canSubmit.value) && !!chat.prompt.value.trim());

function resize() {
	const t = inputEl.value;
	if (!t) return;
	t.style.height = "auto";
	t.style.height = `${Math.min(t.scrollHeight, 160)}px`;
}

function onInput() {
	resize();
	detectMention();
}

/** Show the picker when the caret sits just after an `@token`. */
function detectMention() {
	const el = inputEl.value;
	const caret = el?.selectionStart ?? chat.prompt.value.length;
	const m = chat.prompt.value.slice(0, caret).match(/@([\w-]*)$/);
	mentionActive.value = !!m;
	mentionQuery.value = m ? m[1] : "";
}

function selectPage(p: PageRef) {
	const el = inputEl.value;
	const caret = el?.selectionStart ?? chat.prompt.value.length;
	const head = chat.prompt.value.slice(0, caret).replace(/@([\w-]*)$/, "");
	chat.prompt.value = head + chat.prompt.value.slice(caret);
	targetPage.value = { name: p.name, title: p.page_title || p.name };
	mentionActive.value = false;
	mentionQuery.value = "";
	nextTick(() => inputEl.value?.focus());
}

function onEnter() {
	if (mentionActive.value && filteredPages.value.length) {
		selectPage(filteredPages.value[0]);
		return;
	}
	onSend();
}

function onSend() {
	const text = chat.prompt.value.trim();
	if (!text) return;
	// A referenced page hands off to that page's editor, where the fully-capable
	// in-editor AI applies targeted edits on the canvas.
	if (targetPage.value) {
		const pageId = targetPage.value.name;
		chat.prompt.value = "";
		targetPage.value = null;
		router.push({ name: "builder", params: { pageId }, query: { ai_prompt: text } });
		return;
	}
	chat.send();
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
