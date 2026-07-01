<template>
	<div class="flex h-screen flex-col bg-surface-gray-1">
		<!-- header -->
		<div class="flex items-center justify-between border-b border-outline-gray-1 bg-surface-base px-5 py-3">
			<div class="flex items-center gap-3">
				<Button variant="ghost" iconLeft="lucide-arrow-left" @click="goHome">Dashboard</Button>
				<span class="text-lg font-semibold text-ink-gray-9">{{ headline }}</span>
			</div>
			<div class="flex items-center gap-3">
				<span class="text-sm text-ink-gray-6">{{ subline }}</span>
				<Button
					v-if="isReady"
					variant="solid"
					iconLeft="lucide-upload-cloud"
					:loading="publishing"
					@click="publish">
					Publish site
				</Button>
			</div>
		</div>

		<!-- page grid -->
		<div class="flex-1 overflow-auto p-6">
			<div v-if="!batch" class="pt-20 text-center text-ink-gray-5">Loading…</div>
			<div v-else class="mx-auto grid max-w-5xl grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
				<div
					v-for="page in batch.pages"
					:key="page.route"
					class="flex flex-col gap-2 rounded-lg border border-outline-gray-2 bg-surface-base p-4">
					<div class="flex items-center justify-between gap-2">
						<span class="truncate font-medium text-ink-gray-8" :title="page.page_title">
							{{ page.page_title }}
						</span>
						<span class="rounded-full px-2 py-0.5 text-xs font-medium" :class="pillClass(page.status)">
							{{ statusLabel(page.status) }}
						</span>
					</div>
					<span class="truncate font-mono text-xs text-ink-gray-5">/{{ page.route.replace(/^\//, "") }}</span>
					<div v-if="page.error" class="text-xs text-ink-red-6">{{ page.error }}</div>
					<div class="mt-1 flex gap-2">
						<Button
							v-if="page.status === 'done' && page.page"
							variant="subtle"
							size="sm"
							@click="openPage(page.page)">
							Open in editor
						</Button>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import router from "@/router";
import { Button, createResource, toast } from "frappe-ui";
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

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
	total_pages: number;
	completed_pages: number;
	failed_pages: number;
	pages: BatchPage[];
}

const route = useRoute();
const batchId = route.params.batchId as string;
const batch = ref<Batch | null>(null);
const publishing = ref(false);
let timer: ReturnType<typeof setInterval> | null = null;

const statusResource = createResource({ url: "builder.ai.api.get_site_batch_status" });

const settled = computed(() => {
	const b = batch.value;
	return !!b && b.total_pages > 0 && b.completed_pages + b.failed_pages >= b.total_pages;
});
const isReady = computed(() => settled.value && (batch.value?.completed_pages || 0) > 0);

const headline = computed(() => (isReady.value ? "Your site is ready to review" : "Building your site…"));
const subline = computed(() => {
	const b = batch.value;
	if (!b) return "";
	if (b.status === "architecting") return "Planning the pages…";
	if (b.status === "assets") return "Designing the theme, nav, header & footer…";
	if (!b.total_pages) return "Setting up…";
	return `${b.completed_pages}/${b.total_pages} pages${b.failed_pages ? ` · ${b.failed_pages} failed` : ""}`;
});

async function refresh() {
	try {
		batch.value = await statusResource.submit({ batch_id: batchId });
		if (settled.value && timer) {
			clearInterval(timer);
			timer = null;
		}
	} catch {
		// transient; keep polling
	}
}

function openPage(pageId: string) {
	router.push({ name: "builder", params: { pageId } });
}

function goHome() {
	router.push({ name: "home" });
}

async function publish() {
	if (publishing.value) return;
	publishing.value = true;
	try {
		const res = await createResource({ url: "builder.ai.api.publish_site_batch", method: "POST" }).submit({
			batch_id: batchId,
		});
		toast.success(res?.message || "Site published");
		goHome();
	} catch (e: any) {
		toast.error(e?.messages?.[0] || "Publish failed");
	} finally {
		publishing.value = false;
	}
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

onMounted(() => {
	refresh();
	timer = setInterval(refresh, 2500);
});
onBeforeUnmount(() => timer && clearInterval(timer));
</script>
