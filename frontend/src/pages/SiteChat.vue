<template>
	<div class="flex h-screen bg-surface-gray-1 text-ink-gray-8">
		<!-- Sessions sidebar -->
		<aside class="flex w-64 shrink-0 flex-col border-r border-outline-gray-2 bg-surface-base">
			<div class="flex items-center justify-between px-3 py-3">
				<span class="text-sm font-semibold text-ink-gray-8">Builds</span>
				<Button variant="ghost" iconLeft="lucide-plus" size="sm" @click="newBuild">New</Button>
			</div>
			<div class="flex-1 overflow-auto px-2 pb-3">
				<button
					v-for="b in builds"
					:key="b.batch_id"
					class="mb-1 w-full truncate rounded-md px-2.5 py-2 text-left text-xs leading-snug"
					:class="
						b.batch_id === batchId
							? 'bg-surface-gray-3 text-ink-gray-9'
							: 'text-ink-gray-6 hover:bg-surface-gray-2'
					"
					@click="openBuild(b.batch_id)">
					<div class="truncate font-medium">{{ b.prompt || "Untitled build" }}</div>
					<div class="mt-0.5 text-ink-gray-4">{{ b.completed_pages }}/{{ b.total_pages || "?" }} pages</div>
				</button>
				<p v-if="!builds.length" class="px-2.5 py-2 text-xs text-ink-gray-4">No builds yet.</p>
			</div>
			<Button variant="ghost" iconLeft="lucide-arrow-left" class="m-2" @click="goHome">Dashboard</Button>
		</aside>

		<!-- Main -->
		<main class="flex min-w-0 flex-1 flex-col">
			<div class="flex-1 overflow-auto">
				<div class="mx-auto flex max-w-2xl flex-col gap-4 px-6 py-8">
					<!-- Empty state -->
					<template v-if="!batchId">
						<div class="pt-10 text-center">
							<h1 class="text-2xl font-semibold text-ink-gray-9">What should we build?</h1>
							<p class="mt-2 text-p-base text-ink-gray-6">
								Describe a website or a change — a whole site, or just a page.
							</p>
						</div>
					</template>

					<!-- Conversation -->
					<template v-else>
						<!-- user's ask -->
						<div v-if="batch?.prompt" class="self-end rounded-2xl bg-surface-gray-3 px-4 py-2.5 text-p-sm">
							{{ batch.prompt }}
						</div>

						<!-- live progress timeline -->
						<div class="rounded-xl border border-outline-gray-2 bg-surface-base p-4">
							<Step :state="stepState(0)" label="Planning the pages & design direction" />
							<Step :state="stepState(1)" label="Designing the theme, nav, header & footer" />
							<Step :state="stepState(2)" :label="buildLabel">
								<div v-if="batch?.pages?.length" class="mt-2 grid grid-cols-1 gap-1.5 sm:grid-cols-2">
									<div
										v-for="p in batch.pages"
										:key="p.route"
										class="flex items-center justify-between gap-2 rounded-md border border-outline-gray-2 bg-surface-gray-1 px-2.5 py-1.5">
										<div class="min-w-0">
											<div class="truncate text-xs font-medium text-ink-gray-8">{{ p.page_title }}</div>
											<div class="truncate font-mono text-[11px] text-ink-gray-4">
												/{{ p.route.replace(/^\//, "") }}
											</div>
										</div>
										<div class="flex items-center gap-1.5">
											<span
												class="rounded-full px-1.5 py-0.5 text-[10px] font-medium"
												:class="pillClass(p.status)">
												{{ statusLabel(p.status) }}
											</span>
											<button
												v-if="p.status === 'done' && p.page"
												class="text-[11px] text-ink-blue-6 hover:underline"
												@click="openPage(p.page)">
												Open
											</button>
										</div>
									</div>
								</div>
							</Step>
						</div>

						<!-- ready -->
						<div
							v-if="isReady"
							class="flex items-center justify-between rounded-xl border border-outline-green-2 bg-surface-green-1 p-4">
							<span class="text-p-sm font-medium text-ink-gray-8">Your site is ready to review.</span>
							<Button variant="solid" iconLeft="lucide-upload-cloud" :loading="publishing" @click="publish">
								Publish site
							</Button>
						</div>
						<div
							v-if="batch?.status === 'failed'"
							class="rounded-xl border border-outline-red-2 bg-surface-red-1 p-4 text-p-sm text-ink-red-7">
							The build hit an error. You can start a new one below.
						</div>
					</template>
				</div>
			</div>

			<!-- input -->
			<div class="border-t border-outline-gray-2 bg-surface-base px-6 py-3">
				<div class="mx-auto flex max-w-2xl items-end gap-2">
					<textarea
						ref="inputEl"
						v-model="prompt"
						rows="1"
						:placeholder="inputPlaceholder"
						class="max-h-40 flex-1 resize-none rounded-lg border border-outline-gray-2 bg-surface-gray-1 px-3 py-2 text-p-sm outline-none focus:border-outline-gray-3"
						@keydown.enter.exact.prevent="submit" />
					<Button
						variant="solid"
						iconLeft="lucide-arrow-up"
						:loading="submitting"
						:disabled="!prompt.trim()"
						@click="submit" />
				</div>
			</div>
		</main>
	</div>
</template>

<script setup lang="ts">
import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import { Button, createResource, toast } from "frappe-ui";
import { computed, h, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

// Tiny inline timeline-step renderer (spinner / check / idle + label + slot).
const Step = (props: { state: string; label: string }, { slots }: any) =>
	h("div", { class: "py-1.5" }, [
		h("div", { class: "flex items-center gap-2" }, [
			h(
				"span",
				{
					class: [
						"grid size-4 shrink-0 place-items-center rounded-full text-[10px]",
						props.state === "done"
							? "bg-surface-green-3 text-ink-green-8"
							: props.state === "active"
								? "bg-surface-blue-3 text-ink-blue-8 animate-pulse"
								: "bg-surface-gray-3 text-ink-gray-5",
					],
				},
				props.state === "done" ? "✓" : props.state === "active" ? "•" : "",
			),
			h(
				"span",
				{
					class: ["text-p-sm", props.state === "pending" ? "text-ink-gray-4" : "text-ink-gray-8 font-medium"],
				},
				props.label,
			),
		]),
		slots.default ? h("div", { class: "pl-6" }, slots.default()) : null,
	]);
// Declare props so Vue passes state/label into the first arg (not attrs).
(Step as any).props = ["state", "label"];

interface BatchPage {
	page: string;
	route: string;
	page_title: string;
	status: string;
	error?: string;
}
interface Batch {
	status: string;
	project_folder: string;
	prompt?: string;
	total_pages: number;
	completed_pages: number;
	failed_pages: number;
	pages: BatchPage[];
}

const route = useRoute();
const builderStore = useBuilderStore();
const batchId = computed(() => (route.params.batchId as string) || "");
const batch = ref<Batch | null>(null);
const builds = ref<any[]>([]);
const prompt = ref("");
const submitting = ref(false);
const publishing = ref(false);
let timer: ReturnType<typeof setInterval> | null = null;
let boundEvent: string | null = null;

const ORDER: Record<string, number> = { architecting: 0, assets: 1, generating: 2 };

const settled = computed(() => {
	const b = batch.value;
	return !!b && b.total_pages > 0 && b.completed_pages + b.failed_pages >= b.total_pages;
});
const isReady = computed(() => settled.value && (batch.value?.completed_pages || 0) > 0);
const buildLabel = computed(() => {
	const b = batch.value;
	if (!b || !b.total_pages) return "Building the pages";
	return `Building the pages · ${b.completed_pages}/${b.total_pages}${b.failed_pages ? ` (${b.failed_pages} failed)` : ""}`;
});
const inputPlaceholder = computed(() =>
	batchId.value ? "Start another build…" : "e.g. A site for my coffee roastery — story, menu, contact",
);

function stepState(step: number): "done" | "active" | "pending" {
	const b = batch.value;
	if (!b) return step === 0 ? "active" : "pending";
	const order = ORDER[b.status] ?? 2;
	if (step < order) return "done";
	if (step > order) return "pending";
	// current step
	if (step === 2) return settled.value ? "done" : "active";
	return "active";
}

const statusResource = createResource({ url: "builder.ai.api.get_site_batch_status" });

async function refresh() {
	if (!batchId.value) return;
	try {
		batch.value = await statusResource.submit({ batch_id: batchId.value });
		if (settled.value && timer) {
			clearInterval(timer);
			timer = null;
		}
	} catch {
		/* transient */
	}
}

async function loadBuilds() {
	try {
		builds.value = await createResource({ url: "builder.ai.api.list_site_batches" }).fetch();
	} catch {
		/* ignore */
	}
}

function subscribe() {
	unsubscribe();
	if (!batchId.value || !builderStore.realtime) return;
	boundEvent = `ai_site_${batchId.value}`;
	builderStore.realtime.on(boundEvent, refresh);
}
function unsubscribe() {
	if (boundEvent && builderStore.realtime) builderStore.realtime.off(boundEvent, refresh);
	boundEvent = null;
}

function watchBatch() {
	if (timer) clearInterval(timer);
	batch.value = null;
	if (!batchId.value) return;
	refresh();
	subscribe();
	timer = setInterval(refresh, 3000);
}

async function submit() {
	const brief = prompt.value.trim();
	if (!brief || submitting.value) return;
	submitting.value = true;
	try {
		const res = await createResource({ url: "builder.ai.api.generate_site", method: "POST" }).submit({
			prompt: brief,
		});
		prompt.value = "";
		await loadBuilds();
		router.push({ name: "site-build", params: { batchId: res.batch_id } });
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Could not start the build.");
	} finally {
		submitting.value = false;
	}
}

async function publish() {
	if (publishing.value) return;
	publishing.value = true;
	try {
		const res = await createResource({ url: "builder.ai.api.publish_site_batch", method: "POST" }).submit({
			batch_id: batchId.value,
		});
		toast.success(res?.message || "Published");
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Publish failed");
	} finally {
		publishing.value = false;
	}
}

function openBuild(id: string) {
	router.push({ name: "site-build", params: { batchId: id } });
}
function newBuild() {
	router.push({ name: "site-build-new" });
}
function openPage(pageId: string) {
	router.push({ name: "builder", params: { pageId } });
}
function goHome() {
	router.push({ name: "home" });
}

function statusLabel(s: string) {
	return { queued: "Queued", streaming: "Building", done: "Ready", failed: "Failed" }[s] || s;
}
function pillClass(s: string) {
	return (
		{
			queued: "bg-surface-gray-3 text-ink-gray-6",
			streaming: "bg-surface-blue-2 text-ink-blue-7",
			done: "bg-surface-green-2 text-ink-green-7",
			failed: "bg-surface-red-2 text-ink-red-7",
		}[s] || "bg-surface-gray-3 text-ink-gray-6"
	);
}

watch(batchId, watchBatch);
onMounted(() => {
	loadBuilds();
	watchBatch();
});
onBeforeUnmount(() => {
	if (timer) clearInterval(timer);
	unsubscribe();
});
</script>
