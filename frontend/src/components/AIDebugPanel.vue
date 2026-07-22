<template>
	<div class="flex flex-col gap-5 text-sm text-ink-gray-7">
		<!-- Summary card: status + model, primary stat tiles, context meter -->
		<div class="overflow-hidden rounded-xl border border-outline-gray-2 bg-surface-gray-1">
			<div class="flex items-center justify-between gap-3 border-b border-outline-gray-2 px-3.5 py-2.5">
				<span class="inline-flex items-center gap-1.5 text-xs font-semibold" :class="stopPill.text">
					<span class="size-2 rounded-full" :class="stopPill.dot" />
					{{ stopPill.label }}
				</span>
				<span class="truncate font-mono text-xs text-ink-gray-5" :title="modelLabel">{{ modelLabel }}</span>
			</div>

			<div class="grid grid-cols-2 divide-x divide-y divide-outline-gray-2 sm:grid-cols-4">
				<div v-for="s in primaryStats" :key="s.label" class="flex flex-col gap-1 p-3.5">
					<span class="text-[10px] font-medium uppercase tracking-wide text-ink-gray-5">{{ s.label }}</span>
					<span class="font-mono text-lg font-medium leading-none text-ink-gray-9">{{ s.value }}</span>
					<span v-if="s.sub" class="text-[11px] leading-none" :class="s.subTone || 'text-ink-gray-5'">
						{{ s.sub }}
					</span>
				</div>
			</div>

			<!-- Context-window meter -->
			<div v-if="context" class="flex flex-col gap-1.5 border-t border-outline-gray-2 px-4 py-3">
				<div class="flex items-center justify-between text-[11px] text-ink-gray-5">
					<span class="font-medium uppercase tracking-wide">Context window</span>
					<span class="font-mono">{{ context.used }} / {{ context.total }} · {{ context.pct }}%</span>
				</div>
				<div class="h-1.5 w-full overflow-hidden rounded-full bg-surface-gray-3">
					<div
						class="h-full rounded-full transition-all"
						:class="context.pct > 85 ? 'bg-surface-amber-5' : 'bg-ink-gray-5'"
						:style="{ width: `${Math.max(context.pct, 1)}%` }" />
				</div>
			</div>

			<!-- Secondary line -->
			<div
				class="flex flex-wrap gap-x-4 gap-y-1 border-t border-outline-gray-2 px-4 py-2 text-[11px] text-ink-gray-5">
				<span>{{ tokens.calls || 0 }} LLM call{{ (tokens.calls || 0) === 1 ? "" : "s" }}</span>
				<span class="text-ink-gray-4">·</span>
				<span>{{ fmt(tokens.prompt_tokens) }} prompt</span>
				<span class="text-ink-gray-4">·</span>
				<span>{{ fmt(tokens.completion_tokens) }} completion</span>
			</div>
		</div>

		<!-- Signal badges -->
		<div v-if="signals.length" class="flex flex-wrap gap-1.5">
			<span
				v-for="s in signals"
				:key="s.text"
				class="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium ring-1"
				:class="
					s.tone === 'bad'
						? 'bg-surface-red-2 text-ink-red-8 ring-outline-red-3'
						: 'bg-surface-amber-2 text-ink-amber-8 ring-outline-amber-3'
				">
				<span class="lucide-alert-triangle size-3" />
				{{ s.text }}
			</span>
		</div>

		<!-- Round-by-round trace, as a timeline -->
		<div v-if="trace.length" class="flex flex-col gap-2.5">
			<div class="flex items-baseline justify-between">
				<span class="text-[11px] font-semibold uppercase tracking-wide text-ink-gray-5">Trace</span>
				<span class="text-xs text-ink-gray-4">
					{{ trace.length }} round{{ trace.length === 1 ? "" : "s" }}
				</span>
			</div>
			<div class="flex flex-col">
				<div v-for="(round, idx) in trace" :key="idx" class="relative flex gap-3 pb-4 last:pb-0">
					<div class="flex flex-col items-center">
						<span
							class="z-10 grid size-5 shrink-0 place-items-center rounded-full bg-surface-gray-3 font-mono text-[10px] font-semibold text-ink-gray-6">
							{{ (round.round ?? idx) + 1 }}
						</span>
						<span v-if="idx < trace.length - 1" class="bg-outline-gray-2 -mb-4 mt-1 w-px flex-1" />
					</div>
					<div class="min-w-0 flex-1 pt-0.5">
						<div v-if="round.tools?.length" class="flex flex-col gap-2">
							<div v-for="(tool, ti) in round.tools" :key="ti" class="min-w-0">
								<span
									class="inline-block rounded-md px-2 py-0.5 font-mono text-[11px] font-semibold"
									:class="toolTone(tool.name)">
									{{ tool.name }}
								</span>
								<pre
									v-if="hasArgs(tool.args)"
									class="no-scrollbar mt-1 overflow-x-auto rounded-md bg-surface-gray-2 px-2.5 py-1.5 font-mono text-[10px] leading-snug text-ink-gray-6"
									>{{ tool.args }}</pre
								>
							</div>
						</div>
						<span v-else class="text-xs italic text-ink-gray-4">
							{{ round.text ? "message only" : "no output" }}
						</span>
						<p
							v-if="round.text"
							class="mt-2 whitespace-pre-wrap break-words rounded-md bg-surface-gray-2 px-3 py-2 text-xs leading-relaxed text-ink-gray-7">
							{{ round.text }}
						</p>
					</div>
				</div>
			</div>
		</div>

		<!-- Tool failures -->
		<div v-if="toolFailures.length" class="rounded-lg border border-outline-red-3 bg-surface-red-2 p-3">
			<span class="flex items-center gap-1.5 text-xs font-semibold text-ink-red-8">
				<span class="lucide-x-circle size-3.5" />
				Tool failures
			</span>
			<ul class="mt-1.5 flex flex-col gap-1">
				<li v-for="(f, i) in toolFailures" :key="i" class="font-mono text-[11px] leading-snug text-ink-red-8">
					{{ f }}
				</li>
			</ul>
		</div>

		<!-- Collapsibles -->
		<div class="flex flex-col gap-2">
			<details v-if="perCall.length" class="group rounded-lg border border-outline-gray-2 bg-surface-gray-1">
				<summary
					class="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs font-medium text-ink-gray-6">
					<span class="lucide-chevron-right size-3.5 transition-transform group-open:rotate-90" />
					Per-call tokens
					<span class="text-ink-gray-4">· {{ perCall.length }}</span>
				</summary>
				<div
					class="max-h-48 overflow-y-auto border-t border-outline-gray-2 px-3 py-2 font-mono text-[11px] leading-relaxed text-ink-gray-6">
					<div v-for="(c, i) in perCall" :key="i" class="tabular-nums">
						<span class="text-ink-gray-4">#{{ i + 1 }}</span>
						{{ fmt(c.prompt) }} prompt
						<span v-if="c.cached" class="text-ink-green-6">({{ fmt(c.cached) }} cached)</span>
						· {{ fmt(c.completion) }} completion
						<span v-if="c.cost">· {{ formatCost(c.cost) }}</span>
					</div>
				</div>
			</details>

			<details class="group rounded-lg border border-outline-gray-2 bg-surface-gray-1">
				<summary
					class="flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-xs font-medium text-ink-gray-6">
					<span class="lucide-chevron-right size-3.5 transition-transform group-open:rotate-90" />
					Raw JSON
					<button
						class="ml-auto inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[11px] font-medium text-ink-gray-5 hover:bg-surface-gray-3 hover:text-ink-gray-8"
						@click.prevent="copyRaw">
						<span :class="copied ? 'lucide-check' : 'lucide-copy'" class="size-3" />
						{{ copied ? "copied" : "copy" }}
					</button>
				</summary>
				<pre
					class="no-scrollbar max-h-64 overflow-auto border-t border-outline-gray-2 p-3 font-mono text-[11px] leading-snug text-ink-gray-7"
					>{{ rawJson }}</pre
				>
			</details>
		</div>
	</div>
</template>

<script setup lang="ts">
import { formatCost } from "@/components/ai/format";
import { computed, ref } from "vue";

const props = defineProps<{ debug: Record<string, any> | null }>();

const fmt = (v: number) => (v || 0).toLocaleString();

const STOP_META: Record<string, { label: string; tone: "good" | "bad" | "warn" }> = {
	model_finished: { label: "Finished", tone: "good" },
	generated: { label: "Page generated", tone: "good" },
	max_rounds: { label: "Incomplete — hit round cap", tone: "bad" },
	noop_retry: { label: "No-op corrected", tone: "warn" },
	build_retry: { label: "Build corrected", tone: "warn" },
	noop_unbacked: { label: "Claimed edit, applied nothing", tone: "bad" },
};

const tokens = computed(() => props.debug?.tokens || {});
const trace = computed<any[]>(() => props.debug?.trace || []);
const perCall = computed<any[]>(() => tokens.value.per_call || []);
const toolFailures = computed<string[]>(() => props.debug?.toolFailures || []);

const modelLabel = computed(() => (props.debug?.loopModel || "?").replace(/^openrouter\//, ""));

const stopPill = computed(() => {
	const meta = STOP_META[props.debug?.stopReason] || { label: props.debug?.stopReason || "?", tone: "warn" };
	const map = {
		good: { text: "text-ink-green-7", dot: "bg-surface-green-7" },
		bad: { text: "text-ink-red-7", dot: "bg-surface-red-7" },
		warn: { text: "text-ink-amber-7", dot: "bg-surface-amber-7" },
	}[meta.tone];
	return { label: meta.label, text: map.text, dot: map.dot };
});

// The four headline tiles: cost (credits), tokens (+ cache read), latency, rounds.
const primaryStats = computed(() => {
	const d = props.debug || {};
	const t = tokens.value;
	const secs = ((d.elapsedMs || 0) / 1000).toFixed(1);
	const cachePct =
		t.prompt_tokens && t.cached_tokens ? Math.round((t.cached_tokens / t.prompt_tokens) * 100) : 0;
	return [
		{ label: "Cost", value: t.cost ? formatCost(t.cost) : "—" },
		{
			label: "Tokens",
			value: fmt(t.total_tokens),
			sub: cachePct ? `${cachePct}% cached` : undefined,
			subTone: "text-ink-green-6",
		},
		{ label: "Latency", value: `${secs}s` },
		{ label: "Rounds", value: `${d.rounds ?? trace.value.length}` },
	];
});

// The latest call's prompt is the conversation's current size in the window.
const context = computed(() => {
	const d = props.debug || {};
	const lastPrompt = perCall.value.at(-1)?.prompt || 0;
	if (!d.contextWindow || !lastPrompt) return null;
	return {
		used: fmt(lastPrompt),
		total: fmt(d.contextWindow),
		pct: Math.round((lastPrompt / d.contextWindow) * 100),
	};
});

const signals = computed(() => {
	const d = props.debug || {};
	const out: { text: string; tone: "bad" | "warn" }[] = [];
	if ((d.finishReasons || []).includes("length")) out.push({ text: "truncated (max_tokens)", tone: "bad" });
	if (toolFailures.value.length)
		out.push({ text: `${toolFailures.value.length} tool failure(s)`, tone: "bad" });
	if (d.argsRepaired > 0) out.push({ text: `JSON repaired ×${d.argsRepaired}`, tone: "warn" });
	if (d.streamRetries > 0)
		out.push({ text: `${d.streamRetries} stream retr${d.streamRetries === 1 ? "y" : "ies"}`, tone: "warn" });
	if (d.noopCorrected) out.push({ text: "no-op corrected", tone: "warn" });
	return out;
});

// Colour tool chips by what they do, so a trace reads at a glance. Semantic tokens
// (surface/ink) auto-handle dark mode — light bg-*-2 + dark ink-*-8 reads in both.
const BLUE = "bg-surface-blue-2 text-ink-blue-8"; // read / inspect
const GREEN = "bg-surface-green-2 text-ink-green-8"; // create
const AMBER = "bg-surface-amber-2 text-ink-amber-8"; // mutate
const RED = "bg-surface-red-2 text-ink-red-8"; // delete
const GRAY = "bg-surface-gray-3 text-ink-gray-7"; // converse / misc
const TOOL_TONES: Record<string, string> = {
	read_block: BLUE,
	read_page: BLUE,
	query_blocks: BLUE,
	query_records: BLUE,
	get_page_scripts: BLUE,
	get_document: BLUE,
	list_doctypes: BLUE,
	search_source: BLUE,
	read_source: BLUE,
	preview_page: BLUE,
	add_block: GREEN,
	set_page_script: GREEN,
	generate_page: GREEN,
	create_page: GREEN,
	create_component: GREEN,
	set_design_token: GREEN,
	run_python: GREEN,
	update_block: AMBER,
	update_blocks: AMBER,
	update_script: AMBER,
	move_block: AMBER,
	set_page_settings: AMBER,
	remove_block: RED,
	present_ui: GRAY,
};
const toolTone = (name: string) => TOOL_TONES[name] || GRAY;

// An args blob worth showing (not empty / "{}").
const hasArgs = (args: unknown) => {
	const s = String(args ?? "").trim();
	return s.length > 0 && s !== "{}" && s !== "null";
};

const rawJson = computed(() => JSON.stringify(props.debug || {}, null, 2));
const copied = ref(false);
function copyRaw() {
	if (!navigator.clipboard) return;
	navigator.clipboard.writeText(rawJson.value).then(() => {
		copied.value = true;
		setTimeout(() => (copied.value = false), 1500);
	});
}
</script>
