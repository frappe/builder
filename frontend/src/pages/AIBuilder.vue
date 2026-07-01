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
				<div class="mx-auto max-w-2xl">
					<div
						class="bg-surface-white flex items-end gap-2 rounded-xl border border-outline-gray-2 px-3 py-2 focus-within:border-outline-gray-3">
						<textarea
							ref="inputEl"
							v-model="chat.prompt.value"
							rows="1"
							placeholder="Ask Builder AI…"
							class="max-h-40 min-h-[24px] flex-1 resize-none border-0 bg-transparent text-p-sm leading-relaxed text-ink-gray-9 outline-none placeholder:text-ink-gray-4"
							@input="resize"
							@keydown.enter.exact.prevent="onSend" />
						<Dropdown :options="modelOptions" placement="top-end">
							<button
								class="shrink-0 rounded px-1.5 py-1 text-[11px] text-ink-gray-5 hover:bg-surface-gray-2">
								{{ modelLabel }}
							</button>
						</Dropdown>
						<Button v-if="chat.sending.value" variant="subtle" @click="chat.cancel">
							<template #icon><FeatherIcon name="square" class="size-3.5" /></template>
						</Button>
						<Button v-else variant="solid" :disabled="!chat.canSubmit.value" @click="onSend">
							<template #icon><FeatherIcon name="arrow-up" class="size-4" /></template>
						</Button>
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

const route = useRoute();
const chat = useAgentChat();
const inputEl = ref<HTMLTextAreaElement | null>(null);
const scrollEl = ref<HTMLElement | null>(null);

const routeSessionId = computed(() => (route.params.sessionId as string) || "");
const modelLabel = computed(
	() => chat.models.value.find((m) => m.name === chat.selectedModel.value)?.label || "Model",
);
const modelOptions = computed(() =>
	chat.models.value.map((m) => ({ label: m.label, onClick: () => (chat.selectedModel.value = m.name) })),
);

function resize() {
	const t = inputEl.value;
	if (!t) return;
	t.style.height = "auto";
	t.style.height = `${Math.min(t.scrollHeight, 160)}px`;
}

function onSend() {
	chat.send();
	nextTick(resize);
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
	await boot();
});
onBeforeUnmount(() => chat.teardown());
</script>
