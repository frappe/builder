<template>
	<!-- Bob's changes to other pages: a question with one row per page until answered,
	     then a quiet record of how each page came out. -->
	<div
		class="w-full"
		:class="pending && 'rounded-6 border border-outline-gray-2 bg-surface-gray-1 px-1.5 pb-2.5 pt-2'">
		<div class="flex items-baseline gap-2" :class="pending && 'px-1.5'">
			<p
				class="min-w-0 flex-1"
				:class="pending ? 'text-p-sm font-medium text-ink-gray-8' : 'text-p-xs text-ink-gray-5'">
				{{ pending ? cardQuestion(rows) : cardOutcome(rows, skippedAll) }}
			</p>
			<button
				v-if="pending && interactive && rows.length > 3"
				type="button"
				class="shrink-0 text-p-xs text-ink-gray-5 transition-colors hover:text-ink-gray-8"
				@click="toggleAll">
				{{ unticked.size ? "Select all" : "Select none" }}
			</button>
		</div>
		<p v-if="pending && rows.some((r) => r.isNew)" class="px-1.5 text-p-xs text-ink-gray-5">
			New pages are built one at a time after you apply.
		</p>

		<ul class="m-0 flex list-none flex-col p-0" :class="pending ? 'mt-1.5' : 'mt-1'">
			<li v-for="row in shownRows" :key="row.key">
				<div class="flex min-h-7 items-center gap-2" :class="pending && 'px-1.5'">
					<Checkbox
						v-if="pending && interactive && rows.length > 1"
						:model-value="!unticked.has(row.key)"
						:aria-label="`Include ${row.title}`"
						@update:model-value="toggle(row.key)" />
					<span v-else class="size-3.5 shrink-0" :class="rowIcon(row)" />
					<!-- one truncating line, so a long route gives way before the title -->
					<span class="min-w-0 flex-1 truncate">
						<a
							v-if="row.pageId && row.result?.status !== 'failed'"
							:href="pageHref(row.pageId)"
							class="decoration-outline-gray-4 text-sm underline-offset-2 hover:underline"
							:class="skippedAll || row.result?.status === 'skipped' ? 'text-ink-gray-5' : 'text-ink-gray-8'"
							@click.prevent="emit('open', row.pageId)">
							{{ row.title }}
						</a>
						<span v-else class="text-sm text-ink-gray-8">{{ row.title }}</span>
						<span class="ml-1.5 text-xs text-ink-gray-5">{{ row.route }}</span>
					</span>
					<button
						v-if="row.lines.length"
						type="button"
						class="flex shrink-0 items-center gap-0.5 text-xs text-ink-gray-5 transition-colors hover:text-ink-gray-8"
						:aria-expanded="expanded.has(row.key)"
						@click="toggleLines(row.key)">
						<span class="tabular-nums">{{ rowMeta(row) }}</span>
						<span
							class="lucide-chevron-right size-3 transition-transform"
							:class="expanded.has(row.key) && 'rotate-90'" />
					</button>
				</div>
				<p v-if="row.result?.status === 'failed'" class="mb-1 pl-[22px] text-p-xs text-ink-red-6">
					{{ capitalise(row.result.detail || "Something went wrong") }}
				</p>
				<ul
					v-if="expanded.has(row.key)"
					class="mb-1.5 flex list-none flex-col gap-1 border-l border-outline-gray-2 pl-2.5 text-p-xs text-ink-gray-6"
					:class="pending ? 'ml-[29px] mr-1.5' : 'ml-[7px]'">
					<li v-for="line in row.lines" :key="line" class="line-clamp-2">{{ line }}</li>
				</ul>
			</li>
		</ul>
		<button
			v-if="hiddenCount"
			type="button"
			class="mt-0.5 text-p-xs text-ink-gray-5 transition-colors hover:text-ink-gray-8"
			:class="pending && 'px-1.5'"
			@click="showAll = true">
			{{ shownRows.length ? `Show ${hiddenCount} more` : `Show the ${hiddenCount} pages` }}
		</button>

		<div v-if="pending && interactive" class="mt-2.5 flex gap-2 px-1.5">
			<Button
				variant="solid"
				size="sm"
				:loading="confirming"
				:disabled="busy || !ticked.length"
				@click="emit('apply', [...unticked])">
				{{ applyLabel(ticked) }}
			</Button>
			<Button variant="subtle" size="sm" :disabled="confirming || busy" @click="emit('skip')">Skip</Button>
		</div>
		<p v-else-if="pending" class="mt-1.5 px-1.5 text-p-xs text-ink-gray-5">Not applied</p>
	</div>
</template>

<script setup lang="ts">
import {
	applyLabel,
	cardOutcome,
	cardQuestion,
	cardRows,
	RESULT_ICONS,
	type PageCardRow,
} from "@/components/ai/pageChanges";
import { Button, Checkbox } from "frappe-ui";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

const props = defineProps<{
	metadata: Record<string, any>;
	/** The card still takes a click: it is the chat's last message. */
	interactive: boolean;
	busy?: boolean;
	confirming?: boolean;
}>();

const emit = defineEmits<{
	apply: [skip: string[]];
	skip: [];
	open: [pageId: string];
}>();

// rows past this fold behind "Show N more", so a card for many pages stays short
const FOLD_AFTER = 6;

const rows = computed(() => cardRows(props.metadata));
const pending = computed(() => props.metadata.status === "pending_action");
const skippedAll = computed(() => props.metadata.status === "action_skipped");

const unticked = ref(new Set<string>());
const ticked = computed(() => rows.value.filter((r) => !unticked.value.has(r.key)));
// a lone page has nothing to choose between, so its changes show straight away
const expanded = ref(new Set<string>(rows.value.length === 1 ? [rows.value[0].key] : []));
const showAll = ref(false);

// a card skipped as a whole changed nothing, so it folds down to its one line
const foldAt = computed(() => (skippedAll.value ? 0 : FOLD_AFTER));
const shownRows = computed(() =>
	showAll.value || rows.value.length <= foldAt.value + 1 ? rows.value : rows.value.slice(0, foldAt.value),
);
const hiddenCount = computed(() => rows.value.length - shownRows.value.length);

const flip = (set: Set<string>, key: string) => {
	const next = new Set(set);
	next.has(key) ? next.delete(key) : next.add(key);
	return next;
};
const toggle = (key: string) => (unticked.value = flip(unticked.value, key));
const toggleLines = (key: string) => (expanded.value = flip(expanded.value, key));
const toggleAll = () =>
	(unticked.value = unticked.value.size ? new Set() : new Set(rows.value.map((r) => r.key)));

const router = useRouter();
const pageHref = (pageId: string) => router.resolve({ name: "builder", params: { pageId } }).href;

const capitalise = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

function rowIcon(row: PageCardRow): string {
	if (row.result) return RESULT_ICONS[row.result.status];
	if (skippedAll.value) return RESULT_ICONS.skipped;
	return row.isNew ? "lucide-file-plus text-ink-gray-5" : "lucide-file-pen-line text-ink-gray-5";
}

function rowMeta(row: PageCardRow): string {
	if (row.isNew) return "Brief";
	return `${row.count} ${row.count === 1 ? "change" : "changes"}`;
}
</script>
