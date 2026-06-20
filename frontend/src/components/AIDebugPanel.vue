<template>
	<div class="flex flex-col gap-4 text-ink-gray-7">
		<!-- Summary grid -->
		<div class="grid grid-cols-2 gap-x-6 gap-y-2 text-p-sm sm:grid-cols-3">
			<div v-for="stat in summary" :key="stat.label" class="flex flex-col">
				<span class="text-xs uppercase tracking-wide text-ink-gray-4">{{ stat.label }}</span>
				<span class="font-mono text-ink-gray-8">{{ stat.value }}</span>
			</div>
		</div>

		<!-- Signals -->
		<div v-if="signals.length" class="flex flex-wrap gap-1.5">
			<span
				v-for="s in signals"
				:key="s.text"
				class="rounded-full px-2 py-0.5 text-xs font-medium"
				:class="s.tone === 'bad' ? 'bg-surface-red-2 text-ink-red-3' : 'bg-surface-amber-2 text-ink-amber-3'">
				{{ s.text }}
			</span>
		</div>

		<!-- Per-round trace: what the model did, round by round -->
		<div v-if="trace.length" class="flex flex-col gap-2">
			<span class="text-xs uppercase tracking-wide text-ink-gray-4">Trace ({{ trace.length }} rounds)</span>
			<div
				v-for="(round, idx) in trace"
				:key="idx"
				class="rounded-md border border-outline-gray-1 bg-surface-gray-1 p-2.5">
				<div class="mb-1.5 flex items-center gap-2">
					<span class="rounded bg-surface-gray-3 px-1.5 py-0.5 font-mono text-[10px] text-ink-gray-6">
						round {{ round.round ?? idx }}
					</span>
					<span v-if="!round.tools?.length" class="text-xs italic text-ink-gray-4">no tool calls</span>
				</div>
				<div v-if="round.tools?.length" class="flex flex-col gap-1.5">
					<div v-for="(tool, ti) in round.tools" :key="ti" class="flex flex-col gap-0.5">
						<span class="font-mono text-xs font-medium text-ink-gray-8">{{ tool.name }}</span>
						<span
							v-if="tool.args"
							class="overflow-x-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-snug text-ink-gray-5">
							{{ tool.args }}
						</span>
					</div>
				</div>
				<p v-if="round.text" class="mt-1.5 whitespace-pre-wrap break-words text-xs text-ink-gray-6">
					“{{ round.text }}”
				</p>
			</div>
		</div>

		<!-- Tool failures -->
		<div v-if="toolFailures.length" class="flex flex-col gap-1">
			<span class="text-xs uppercase tracking-wide text-ink-red-3">Tool failures</span>
			<span v-for="(f, i) in toolFailures" :key="i" class="font-mono text-[11px] leading-snug text-ink-red-3">
				{{ f }}
			</span>
		</div>

		<!-- Per-call token breakdown -->
		<details v-if="perCall.length" class="text-p-sm">
			<summary class="cursor-pointer text-xs uppercase tracking-wide text-ink-gray-4">
				Per-call tokens ({{ perCall.length }})
			</summary>
			<div class="mt-1.5 max-h-48 overflow-y-auto font-mono text-[11px] leading-relaxed text-ink-gray-6">
				<div v-for="(c, i) in perCall" :key="i">
					#{{ i + 1 }} · {{ fmt(c.prompt) }} prompt{{ c.cached ? ` (${fmt(c.cached)} cached)` : "" }} ·
					{{ fmt(c.completion) }} completion
				</div>
			</div>
		</details>

		<!-- Raw -->
		<details class="text-p-sm">
			<summary class="cursor-pointer text-xs uppercase tracking-wide text-ink-gray-4">Raw JSON</summary>
			<pre
				class="mt-1.5 max-h-64 overflow-auto rounded-md bg-surface-gray-2 p-2 font-mono text-[11px] leading-snug text-ink-gray-7"
				>{{ rawJson }}</pre
			>
		</details>
	</div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{ debug: Record<string, any> | null }>();

const fmt = (v: number) => (v || 0).toLocaleString();

const STOP_LABELS: Record<string, string> = {
	model_finished: "model finished",
	generated: "page generated",
	max_rounds: "hit round cap (incomplete)",
	noop_retry: "no-op corrected",
	noop_unbacked: "claimed edit, applied nothing",
};

const tokens = computed(() => props.debug?.tokens || {});
const trace = computed<any[]>(() => props.debug?.trace || []);
const perCall = computed<any[]>(() => tokens.value.per_call || []);
const toolFailures = computed<string[]>(() => props.debug?.toolFailures || []);

const summary = computed(() => {
	const d = props.debug || {};
	const t = tokens.value;
	const secs = ((d.elapsedMs || 0) / 1000).toFixed(1);
	const cached = t.cached_tokens ? ` (${fmt(t.cached_tokens)} cached)` : "";
	return [
		{ label: "Model", value: (d.loopModel || "?").replace(/^openrouter\//, "") },
		{ label: "Stop reason", value: STOP_LABELS[d.stopReason] || d.stopReason || "?" },
		{ label: "Rounds", value: `${d.rounds ?? trace.value.length}` },
		{ label: "Latency", value: `${secs}s` },
		{ label: "Total tokens", value: `${fmt(t.total_tokens)}${cached}` },
		{ label: "Prompt / completion", value: `${fmt(t.prompt_tokens)} / ${fmt(t.completion_tokens)}` },
	];
});

const signals = computed(() => {
	const d = props.debug || {};
	const out: { text: string; tone: "bad" | "warn" }[] = [];
	if ((d.finishReasons || []).includes("length")) out.push({ text: "truncated (max_tokens)", tone: "bad" });
	if (toolFailures.value.length)
		out.push({ text: `${toolFailures.value.length} tool failure(s)`, tone: "bad" });
	if (d.stopReason === "max_rounds") out.push({ text: "incomplete — hit round cap", tone: "bad" });
	if (d.stopReason === "noop_unbacked") out.push({ text: "claimed edit, applied nothing", tone: "bad" });
	if (d.argsRepaired > 0) out.push({ text: `JSON repaired ×${d.argsRepaired}`, tone: "warn" });
	if (d.noopCorrected) out.push({ text: "no-op corrected", tone: "warn" });
	return out;
});

const rawJson = computed(() => JSON.stringify(props.debug || {}, null, 2));
</script>
