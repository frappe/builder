<template>
	<div class="flex flex-col gap-4 text-sm text-ink-gray-7">
		<!-- Header: verdict + model + key metrics -->
		<div class="flex flex-col gap-3 rounded-lg border border-outline-gray-2 bg-surface-gray-1 p-3">
			<div class="flex items-center justify-between gap-3">
				<span class="rounded-full px-2.5 py-1 text-xs font-semibold ring-1" :class="stopPill.class">
					{{ stopPill.label }}
				</span>
				<span class="truncate font-mono text-xs text-ink-gray-5" :title="modelLabel">{{ modelLabel }}</span>
			</div>
			<div class="grid grid-cols-3 gap-x-4 gap-y-3">
				<div v-for="m in metrics" :key="m.label" class="flex flex-col gap-0.5">
					<span class="text-xs text-ink-gray-5">{{ m.label }}</span>
					<span class="font-mono text-sm text-ink-gray-8">{{ m.value }}</span>
				</div>
			</div>
		</div>

		<!-- Signal badges -->
		<div v-if="signals.length" class="flex flex-wrap gap-1.5">
			<span
				v-for="s in signals"
				:key="s.text"
				class="rounded-full px-2.5 py-1 text-xs font-medium ring-1"
				:class="
					s.tone === 'bad'
						? 'bg-surface-red-2 text-ink-red-8 ring-outline-red-3'
						: 'bg-surface-amber-2 text-ink-amber-8 ring-outline-amber-3'
				">
				{{ s.text }}
			</span>
		</div>

		<!-- Round-by-round trace -->
		<div v-if="trace.length" class="flex flex-col gap-2">
			<div class="flex items-baseline justify-between">
				<span class="text-xs font-semibold text-ink-gray-5">Trace</span>
				<span class="text-xs text-ink-gray-4">{{ trace.length }} rounds</span>
			</div>
			<div class="flex flex-col gap-2">
				<div
					v-for="(round, idx) in trace"
					:key="idx"
					class="bg-surface-white rounded-lg border border-outline-gray-1 p-3">
					<div class="mb-2 flex items-center gap-2">
						<span
							class="grid size-5 place-items-center rounded-full bg-surface-gray-3 font-mono text-[10px] font-semibold text-ink-gray-7">
							{{ (round.round ?? idx) + 1 }}
						</span>
						<span v-if="!round.tools?.length" class="text-xs italic text-ink-gray-4">
							{{ round.text ? "message only" : "no output" }}
						</span>
					</div>
					<div v-if="round.tools?.length" class="flex flex-col gap-2">
						<div v-for="(tool, ti) in round.tools" :key="ti">
							<span
								class="inline-block rounded px-1.5 py-0.5 font-mono text-[11px] font-semibold"
								:class="toolTone(tool.name)">
								{{ tool.name }}
							</span>
							<pre
								v-if="tool.args"
								class="mt-1 overflow-x-auto rounded bg-surface-gray-2 px-2 py-1 font-mono text-[10px] leading-snug text-ink-gray-6"
								>{{ tool.args }}</pre
							>
						</div>
					</div>
					<p
						v-if="round.text"
						class="mt-2 whitespace-pre-wrap break-words border-l-2 border-outline-gray-3 pl-2 text-xs italic text-ink-gray-6">
						{{ round.text }}
					</p>
				</div>
			</div>
		</div>

		<!-- Tool failures -->
		<div v-if="toolFailures.length" class="rounded-lg border border-outline-red-3 bg-surface-red-2 p-3">
			<span class="text-xs font-semibold text-ink-red-8">Tool failures</span>
			<ul class="mt-1.5 flex flex-col gap-1">
				<li v-for="(f, i) in toolFailures" :key="i" class="font-mono text-[11px] leading-snug text-ink-red-8">
					{{ f }}
				</li>
			</ul>
		</div>

		<!-- Per-call token breakdown -->
		<details v-if="perCall.length" class="rounded-lg border border-outline-gray-1 px-3 py-2">
			<summary class="cursor-pointer text-xs font-semibold text-ink-gray-5">
				Per-call tokens · {{ perCall.length }}
			</summary>
			<div class="mt-2 max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-ink-gray-6">
				<div v-for="(c, i) in perCall" :key="i">
					#{{ i + 1 }} · {{ fmt(c.prompt) }} prompt{{ c.cached ? ` (${fmt(c.cached)} cached)` : "" }} ·
					{{ fmt(c.completion) }} completion
				</div>
			</div>
		</details>

		<!-- Raw JSON + copy -->
		<details class="rounded-lg border border-outline-gray-1 px-3 py-2">
			<summary class="flex cursor-pointer items-center justify-between text-xs font-semibold text-ink-gray-5">
				Raw JSON
				<button
					class="text-[10px] font-medium normal-case text-ink-gray-5 hover:text-ink-gray-8"
					@click.prevent="copyRaw">
					{{ copied ? "copied ✓" : "copy" }}
				</button>
			</summary>
			<pre
				class="mt-2 max-h-64 overflow-auto rounded bg-surface-gray-2 p-2 font-mono text-[11px] leading-snug text-ink-gray-7"
				>{{ rawJson }}</pre
			>
		</details>
	</div>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";

const props = defineProps<{ debug: Record<string, any> | null }>();

const fmt = (v: number) => (v || 0).toLocaleString();

const STOP_META: Record<string, { label: string; tone: "good" | "bad" | "warn" }> = {
	model_finished: { label: "Finished", tone: "good" },
	generated: { label: "Page generated", tone: "good" },
	max_rounds: { label: "Incomplete — hit round cap", tone: "bad" },
	noop_retry: { label: "No-op corrected", tone: "warn" },
	noop_unbacked: { label: "Claimed edit, applied nothing", tone: "bad" },
};

const tokens = computed(() => props.debug?.tokens || {});
const trace = computed<any[]>(() => props.debug?.trace || []);
const perCall = computed<any[]>(() => tokens.value.per_call || []);
const toolFailures = computed<string[]>(() => props.debug?.toolFailures || []);

const modelLabel = computed(() => (props.debug?.loopModel || "?").replace(/^openrouter\//, ""));

const stopPill = computed(() => {
	const meta = STOP_META[props.debug?.stopReason] || { label: props.debug?.stopReason || "?", tone: "warn" };
	const cls = {
		good: "bg-surface-green-2 text-ink-green-8 ring-1 ring-outline-green-3",
		bad: "bg-surface-red-2 text-ink-red-8 ring-1 ring-outline-red-3",
		warn: "bg-surface-amber-2 text-ink-amber-8 ring-1 ring-outline-amber-3",
	}[meta.tone];
	return { label: meta.label, class: cls };
});

const metrics = computed(() => {
	const d = props.debug || {};
	const t = tokens.value;
	const secs = ((d.elapsedMs || 0) / 1000).toFixed(1);
	const cached = t.cached_tokens ? ` (${fmt(t.cached_tokens)} cached)` : "";
	return [
		{ label: "Rounds", value: `${d.rounds ?? trace.value.length}` },
		{ label: "LLM calls", value: `${t.calls || 0}` },
		{ label: "Latency", value: `${secs}s` },
		{ label: "Total tokens", value: `${fmt(t.total_tokens)}${cached}` },
		{ label: "Prompt", value: fmt(t.prompt_tokens) },
		{ label: "Completion", value: fmt(t.completion_tokens) },
	];
});

const signals = computed(() => {
	const d = props.debug || {};
	const out: { text: string; tone: "bad" | "warn" }[] = [];
	if ((d.finishReasons || []).includes("length")) out.push({ text: "truncated (max_tokens)", tone: "bad" });
	if (toolFailures.value.length)
		out.push({ text: `${toolFailures.value.length} tool failure(s)`, tone: "bad" });
	if (d.argsRepaired > 0) out.push({ text: `JSON repaired ×${d.argsRepaired}`, tone: "warn" });
	if (d.noopCorrected) out.push({ text: "no-op corrected", tone: "warn" });
	return out;
});

// Colour tool chips by what they do, so a trace reads at a glance. Semantic tokens
// (surface/ink) auto-handle dark mode — light bg-*-1 + dark ink-*-3 reads in both.
const BLUE = "bg-surface-blue-2 text-ink-blue-8"; // read / inspect
const GREEN = "bg-surface-green-2 text-ink-green-8"; // create
const AMBER = "bg-surface-amber-2 text-ink-amber-8"; // mutate
const RED = "bg-surface-red-2 text-ink-red-8"; // delete
const GRAY = "bg-surface-gray-3 text-ink-gray-7"; // converse
const TOOL_TONES: Record<string, string> = {
	read_block: BLUE,
	query_blocks: BLUE,
	get_page_scripts: BLUE,
	add_block: GREEN,
	set_page_script: GREEN,
	generate_page: GREEN,
	update_block: AMBER,
	update_blocks: AMBER,
	update_script: AMBER,
	move_block: AMBER,
	remove_block: RED,
	propose_plan: GRAY,
	ask_clarification: GRAY,
};
const toolTone = (name: string) => TOOL_TONES[name] || GRAY;

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
