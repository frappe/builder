<template>
	<div class="mt-2 overflow-hidden rounded-lg border border-outline-gray-2">
		<div class="flex items-center justify-between border-b border-outline-gray-2 bg-surface-gray-1 px-3 py-2">
			<span class="text-xs font-medium text-ink-gray-7">
				{{ header }}
			</span>
			<span class="text-xs tabular-nums text-ink-gray-5">{{ batch.completed }}/{{ batch.total || "?" }}</span>
		</div>
		<div class="divide-y divide-outline-gray-1">
			<div v-for="t in batch.tasks" :key="t.row" class="flex items-center gap-2.5 px-3 py-2">
				<span class="grid size-4 shrink-0 place-items-center">
					<span v-if="t.status === 'done'" class="text-ink-gray-7">✓</span>
					<span v-else-if="t.status === 'failed'" class="text-ink-gray-5">✕</span>
					<span v-else-if="t.status === 'running'" class="bg-ink-gray-6 size-2 animate-pulse rounded-full" />
					<span v-else class="size-2 rounded-full border border-outline-gray-3" />
				</span>
				<img
					v-if="t.preview && t.status === 'done'"
					:src="t.preview"
					class="h-9 w-14 shrink-0 rounded border border-outline-gray-2 object-cover object-top"
					alt="" />
				<span class="min-w-0 flex-1 truncate text-xs text-ink-gray-8">{{ t.title }}</span>
				<button
					v-if="t.status === 'done' && t.page"
					class="shrink-0 text-xs text-ink-gray-6 hover:text-ink-gray-9 hover:underline"
					@click="openPage(t.page)">
					Open
				</button>
				<span v-else-if="t.status === 'failed'" class="shrink-0 text-[11px] text-ink-gray-4">failed</span>
			</div>
		</div>
		<div
			v-if="settled && batch.projectFolder"
			class="flex items-center justify-between border-t border-outline-gray-2 bg-surface-gray-1 px-3 py-2">
			<span class="text-xs text-ink-gray-5">{{ batch.completed }} page(s) ready to review</span>
			<Button size="sm" variant="subtle" :loading="publishing" @click="$emit('publish', batch.batchId)">
				Publish
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import router from "@/router";
import { Button } from "frappe-ui";
import { computed } from "vue";
import type { BatchState } from "./useAgentChat";

const props = defineProps<{ batch: BatchState; publishing?: boolean }>();
defineEmits<{ (e: "publish", batchId: string): void }>();

const settled = computed(
	() => ["done", "failed", "cancelled"].includes(props.batch.status) && props.batch.completed > 0,
);
const header = computed(() =>
	settled.value
		? "Pages built"
		: `Building ${props.batch.total || ""} page${props.batch.total === 1 ? "" : "s"}…`,
);

function openPage(pageId: string) {
	router.push({ name: "builder", params: { pageId } });
}
</script>
