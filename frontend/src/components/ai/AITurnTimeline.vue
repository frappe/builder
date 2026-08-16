<template>
	<div v-if="steps.length" class="flex w-full flex-col gap-1.5">
		<template v-for="step in rows" :key="step.id">
			<!-- thinking: collapsed to a single line. Only expandable when the provider
			     actually streamed reasoning — an empty disclosure is a dead affordance,
			     and once it's over with nothing to show it isn't worth a row at all
			     (which is also how it comes back on reload).
			     A literal <button>, never <component :is="'button'">: Vue capitalizes
			     the string and finds frappe-ui's registered Button, which arrives with
			     a full pill treatment. -->
			<button
				v-if="step.kind === 'thinking' && (running(step) || step.text)"
				type="button"
				class="flex w-fit items-center gap-1 text-left text-p-xs text-ink-gray-5"
				:class="step.text ? 'hover:text-ink-gray-7' : 'cursor-default'"
				:disabled="!step.text"
				@click="toggle(step.id)">
				<span :class="running(step) && 'animate-shine'">
					{{ running(step) ? "Thinking" : "Thought" }}
				</span>
				<span v-if="duration(step.ms)" class="tabular-nums text-ink-gray-4">{{ duration(step.ms) }}</span>
				<!-- Disclosure chevron TRAILS the label: the label sits flush on the
				     container edge (one line with the reply below and the "Working" row it
				     replaces), and the chevron appearing once reasoning streams shifts
				     nothing to its left. -->
				<span
					v-if="step.text"
					class="lucide-chevron-right size-3 shrink-0 transition-transform"
					:class="expanded.has(step.id) && 'rotate-90'" />
			</button>
			<!-- Reasoning arrives as markdown ("**Sorting visual elements**"), so render
			     it — as raw text the asterisks were on show. Muted and tight: it is an
			     aside you opened, not the answer. The rule hangs under the chevron. -->
			<div
				v-if="step.kind === 'thinking' && step.text && expanded.has(step.id)"
				class="ai-thought prose prose-sm max-w-none break-words border-l border-outline-gray-2 pl-3 text-p-xs text-ink-gray-5"
				v-html="renderMarkdown(step.text)" />

			<!-- tool: what Bob actually ran -->
			<div v-else-if="step.kind === 'tool'" class="flex items-center gap-2 text-p-xs">
				<span class="size-3.5 shrink-0 text-ink-gray-5" :class="toolIcon(step.tool)" />
				<span class="min-w-0 truncate text-ink-gray-7" :class="running(step) && 'animate-shine'">
					{{ step.summary }}
				</span>
				<span v-if="step.repeats" class="shrink-0 tabular-nums text-ink-gray-4">×{{ step.repeats }}</span>
				<span v-if="duration(step.ms)" class="ml-auto shrink-0 tabular-nums text-ink-gray-4">
					{{ duration(step.ms) }}
				</span>
			</div>

			<!-- text: what Bob said on its way through -->
			<div
				v-else-if="step.kind === 'text' && step.text"
				class="ai-prose prose prose-sm max-w-none break-words text-p-sm text-ink-gray-7"
				v-html="renderMarkdown(step.text)" />
		</template>

		<!-- The turn's idle stretches (tool arguments streaming, the next round
		     opening) live HERE, as the timeline's tail row, flush left like the
		     thinking row — its most common fate is becoming "Thinking" in place,
		     with no layout shift. -->
		<div v-if="working" class="animate-shine w-fit text-p-xs text-ink-gray-5">Working</div>
	</div>
</template>

<script setup lang="ts">
import { renderMarkdown } from "@/components/ai/markdown";
import type { AITurnStep } from "@/components/ai/types";
import { computed, ref } from "vue";

/** The steps of one assistant turn, in the order they happened. Fed live from
 * `ai_chat_step` events and rehydrated from message metadata on reload, so a
 * turn reads the same whether you watched it or came back to it. `working`
 * appends the turn's idle shimmer as the tail row (see template). */
const props = defineProps<{ steps: AITurnStep[]; working?: boolean }>();

/** A run of the same tool collapses to one row with a count. Minting six design
 * tokens is one action to the reader, not six lines of "Set theme variable", and
 * the repetition drowns out the steps that actually differ. Times are summed. */
const rows = computed<(AITurnStep & { repeats?: number })[]>(() => {
	const out: (AITurnStep & { repeats?: number })[] = [];
	for (const step of props.steps) {
		const last = out[out.length - 1];
		if (last && step.kind === "tool" && last.kind === "tool" && last.summary === step.summary) {
			last.repeats = (last.repeats || 1) + 1;
			last.ms = (last.ms || 0) + (step.ms || 0);
			last.status = step.status;
			continue;
		}
		out.push({ ...step });
	}
	return out;
});

const expanded = ref(new Set<number>());

function toggle(id: number) {
	const next = new Set(expanded.value);
	next.has(id) ? next.delete(id) : next.add(id);
	expanded.value = next;
}

const running = (step: AITurnStep) => step.status === "running";

/** Short and honest: tenths under a minute (most steps land there), m/s above.
 * Anything under 100ms reads as "0.0s", which is noise pretending to be data —
 * a local write that took no time gets no timing at all. */
function duration(ms?: number): string {
	if (!ms || ms < 100) return "";
	if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
	const secs = Math.round(ms / 1000);
	return secs % 60 ? `${Math.floor(secs / 60)}m ${secs % 60}s` : `${Math.floor(secs / 60)}m`;
}

const TOOL_ICONS: Record<string, string> = {
	generate_page: "lucide-layout-template",
	preview_page: "lucide-camera",
	read_block: "lucide-square-dashed",
	query_blocks: "lucide-search",
	search_images: "lucide-image",
	set_design_token: "lucide-palette",
	set_page_script: "lucide-code",
	update_script: "lucide-code",
	create_component: "lucide-box",
	extract_component: "lucide-box",
	write_page_data_script: "lucide-database",
	list_doctypes: "lucide-database",
	get_doctype_schema: "lucide-database",
	query_records: "lucide-database",
	get_document: "lucide-file-text",
	remember: "lucide-bookmark",
	read_page: "lucide-book-open",
	read_url: "lucide-globe",
	research: "lucide-telescope",
	run_python: "lucide-terminal",
	set_page_settings: "lucide-settings-2",
	get_page_scripts: "lucide-code",
	seed_sample_data: "lucide-database",
	create_doctype: "lucide-database",
	connect_form: "lucide-link-2",
	edit_global_settings: "lucide-settings",
	set_home_page: "lucide-home",
};

const toolIcon = (tool?: string) => TOOL_ICONS[tool || ""] || "lucide-wrench";
</script>

<style scoped>
/* An opened thought is an aside, not the answer: prose's heading scale and
 * paragraph rhythm would give it more weight than the reply it led to. Flatten
 * everything to the muted size the row itself uses, keeping only emphasis and
 * list structure. */
.ai-thought :deep(*) {
	font-size: inherit;
	font-weight: inherit;
	color: inherit;
	line-height: 1.55;
}
.ai-thought :deep(strong) {
	font-weight: 600;
	color: var(--ink-gray-6);
}
.ai-thought :deep(p),
.ai-thought :deep(ul),
.ai-thought :deep(ol),
.ai-thought :deep(pre) {
	margin: 0 0 0.6em;
}
.ai-thought :deep(> *:last-child) {
	margin-bottom: 0;
}
</style>
