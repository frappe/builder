<template>
	<div class="flex flex-col gap-2.5">
		<div v-for="row in rows" :key="row.key" class="flex items-start gap-2">
			<span class="mt-0.5 size-3.5 shrink-0" :class="STATE_ICONS[row.state]" />
			<div class="min-w-0 flex-1">
				<div class="flex min-w-0 items-baseline gap-1.5">
					<span class="truncate text-sm text-ink-gray-8">{{ row.title }}</span>
					<span class="shrink-0 truncate text-p-xs text-ink-gray-5">{{ row.route }}</span>
				</div>
				<p
					v-for="line in row.lines"
					:key="line"
					class="text-p-xs text-ink-gray-6"
					:class="row.state === 'new' && 'line-clamp-2'">
					{{ line }}
				</p>
			</div>
			<Button
				v-if="row.pageId && OPENABLE.has(row.state)"
				variant="ghost"
				size="sm"
				class="-my-1 shrink-0"
				@click="router.push({ name: 'builder', params: { pageId: row.pageId } })">
				Open
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { PageRow, PageRowState } from "@/components/ai/pageChanges";
import { Button } from "frappe-ui";
import { useRouter } from "vue-router";

/** Pages a Bob message is about: proposed on a confirm card, or how each came out. */
defineProps<{ rows: PageRow[] }>();

const router = useRouter();

const STATE_ICONS: Record<PageRowState, string> = {
	new: "lucide-file-plus text-ink-gray-5",
	edit: "lucide-file-pen-line text-ink-gray-5",
	created: "lucide-circle-check text-ink-green-6",
	changed: "lucide-circle-check text-ink-green-6",
	built: "lucide-circle-check text-ink-green-6",
	failed: "lucide-circle-alert text-ink-red-6",
};

const OPENABLE = new Set<PageRowState>(["edit", "created", "changed", "built"]);
</script>
