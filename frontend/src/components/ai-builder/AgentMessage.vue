<template>
	<!-- user -->
	<div v-if="message.role === 'user'" class="flex justify-end">
		<div
			class="max-w-[85%] whitespace-pre-wrap rounded-2xl bg-surface-gray-3 px-3.5 py-2 text-p-sm text-ink-gray-8">
			{{ message.text }}
		</div>
	</div>

	<!-- assistant -->
	<div v-else class="flex flex-col gap-2">
		<!-- live tool activity feed (research, edits, screenshots) -->
		<div v-if="message.activity?.length" class="flex flex-col gap-1">
			<template v-for="a in message.activity" :key="a.id">
				<div class="flex items-center gap-2 text-xs text-ink-gray-5">
					<span
						v-if="a.status === 'running'"
						class="bg-ink-gray-6 size-2 shrink-0 animate-pulse rounded-full" />
					<span v-else class="shrink-0 text-ink-gray-6">✓</span>
					<span class="truncate">{{ a.summary }}</span>
				</div>
				<img
					v-if="a.imageUrl"
					:src="a.imageUrl"
					class="max-w-[320px] rounded-md border border-outline-gray-2"
					alt="Page screenshot" />
			</template>
		</div>

		<!-- working indicator while running with no text yet -->
		<div v-if="isWorking" class="flex items-center gap-2 text-ink-gray-5">
			<span class="ab-dots">
				<span></span>
				<span></span>
				<span></span>
			</span>
			<span class="text-p-sm">{{ message.progress || "Working…" }}</span>
		</div>

		<!-- body text -->
		<div
			v-if="message.text && !isPlan"
			class="whitespace-pre-wrap text-p-sm leading-relaxed"
			:class="message.status === 'error' ? 'text-ink-red-6' : 'text-ink-gray-8'">
			{{ message.text }}
		</div>

		<!-- plan summary -->
		<div v-if="isPlan" class="rounded-lg border border-outline-gray-2 p-3">
			<div class="text-p-sm font-medium text-ink-gray-9">{{ message.plan!.headline }}</div>
			<ul v-if="message.plan!.sections.length" class="mt-1.5 flex flex-col gap-1">
				<li v-for="(s, i) in message.plan!.sections" :key="i" class="text-xs text-ink-gray-6">— {{ s }}</li>
			</ul>
			<div v-if="message.plan!.palette" class="mt-2 text-xs text-ink-gray-5">{{ message.plan!.palette }}</div>
			<Button class="mt-3" size="sm" variant="subtle" @click="$emit('approve-plan')">
				Looks good — build it
			</Button>
		</div>

		<!-- clarify options -->
		<div v-if="message.status === 'clarification' && message.options?.length" class="flex flex-wrap gap-1.5">
			<button
				v-for="(opt, i) in message.options"
				:key="i"
				class="flex items-center gap-2 rounded-lg border border-outline-gray-2 px-3 py-1.5 text-xs text-ink-gray-8 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-2"
				@click="$emit('select-option', opt)">
				<span v-if="swatch(i)" class="flex gap-0.5">
					<span
						v-for="(c, j) in swatch(i)"
						:key="j"
						class="size-3 rounded-full"
						:style="{ backgroundColor: c }" />
				</span>
				{{ opt }}
			</button>
		</div>

		<!-- confirm card (sensitive action) -->
		<div v-if="message.confirm" class="rounded-lg border border-outline-gray-2 p-3">
			<div class="flex items-center gap-2">
				<span class="grid size-5 place-items-center rounded-md bg-surface-gray-2 text-ink-gray-7">
					<FeatherIcon name="shield" class="size-3.5" />
				</span>
				<span class="text-p-sm font-medium text-ink-gray-9">{{ confirmTitle }}</span>
			</div>
			<pre v-if="confirmPreview" class="ab-code mt-2">{{ confirmPreview }}</pre>
			<div class="mt-2.5 flex justify-end gap-1.5">
				<Button size="sm" variant="ghost" @click="$emit('confirm', message, 'skip')">Skip</Button>
				<Button size="sm" variant="subtle" @click="$emit('confirm', message, 'apply')">Apply</Button>
			</div>
		</div>

		<!-- parallel task group -->
		<TaskGroupCard
			v-if="batch"
			:batch="batch"
			:publishing="publishing"
			@publish="(id) => $emit('publish', id)" />
	</div>
</template>

<script setup lang="ts">
import { Button, FeatherIcon } from "frappe-ui";
import { computed } from "vue";
import TaskGroupCard from "./TaskGroupCard.vue";
import type { AgentMessage, BatchState } from "./useAgentChat";

const props = defineProps<{ message: AgentMessage; batch?: BatchState | null; publishing?: boolean }>();
defineEmits<{
	(e: "select-option", option: string): void;
	(e: "approve-plan"): void;
	(e: "confirm", message: AgentMessage, decision: "apply" | "skip"): void;
	(e: "publish", batchId: string): void;
}>();

const isPlan = computed(() => props.message.status === "plan_summary" && !!props.message.plan);
const isWorking = computed(
	() => props.message.status === "running" && !props.message.text && !props.message.batchId,
);
const confirmTitle = computed(() => (props.message.text || "Confirm this change?").split("\n")[0]);
const confirmPreview = computed(() => {
	const p = props.message.confirm?.payload;
	if (!p) return "";
	try {
		return JSON.stringify(p, null, 2);
	} catch {
		return "";
	}
});

function swatch(i: number): string[] | null {
	const p = props.message.previews?.[i];
	return p?.colors?.length ? p.colors : null;
}
</script>

<style scoped>
.ab-dots {
	display: inline-flex;
	gap: 3px;
}
.ab-dots span {
	width: 5px;
	height: 5px;
	border-radius: 50%;
	background: currentColor;
	animation: ab-bounce 1.4s infinite ease-in-out both;
}
.ab-dots span:nth-child(1) {
	animation-delay: -0.32s;
}
.ab-dots span:nth-child(2) {
	animation-delay: -0.16s;
}
@keyframes ab-bounce {
	0%,
	80%,
	100% {
		transform: scale(0);
		opacity: 0.4;
	}
	40% {
		transform: scale(1);
		opacity: 1;
	}
}
.ab-code {
	margin: 0;
	max-height: 220px;
	overflow: auto;
	white-space: pre-wrap;
	word-break: break-word;
	border-radius: 6px;
	background: var(--surface-gray-1);
	padding: 8px 10px;
	font-family: var(--font-stack-monospace, ui-monospace, monospace);
	font-size: 11.5px;
	line-height: 1.5;
	color: var(--ink-gray-7);
}
</style>
