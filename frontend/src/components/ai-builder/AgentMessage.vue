<template>
	<!-- user -->
	<div v-if="message.role === 'user'" class="flex justify-end">
		<div class="bg-surface-white max-w-[88%] rounded-md border px-3 py-2 text-p-sm text-ink-gray-8 shadow-sm">
			<img
				v-if="message.attachedImage"
				:src="message.attachedImage"
				class="mb-1.5 max-h-32 rounded border border-outline-gray-2"
				alt="Attached image" />
			<div class="whitespace-pre-wrap break-words">{{ message.text }}</div>
		</div>
	</div>

	<!-- assistant -->
	<div v-else class="flex flex-col gap-2">
		<!-- while running: ONE quiet line — the current step (or the model's narration) -->
		<div v-if="isRunning" class="flex items-center gap-2 text-ink-gray-5">
			<span class="ab-dots">
				<span></span>
				<span></span>
				<span></span>
			</span>
			<span class="text-p-sm">{{ workingLine }}</span>
		</div>

		<!-- once settled: the steps collapse into a small disclosure -->
		<div v-else-if="activityDisplay.length" class="flex flex-col gap-1">
			<button
				class="flex w-fit items-center gap-1 text-xs text-ink-gray-4 transition-colors hover:text-ink-gray-7"
				@click="stepsOpen = !stepsOpen">
				<FeatherIcon :name="stepsOpen ? 'chevron-down' : 'chevron-right'" class="size-3" />
				{{ stepCount }} step{{ stepCount === 1 ? "" : "s" }}
			</button>
			<template v-if="stepsOpen">
				<div
					v-for="a in activityDisplay"
					:key="a.id"
					class="group flex items-center gap-2 pl-4 text-xs text-ink-gray-5">
					<span class="shrink-0 text-ink-gray-6">✓</span>
					<span class="truncate">
						{{ a.summary }}
						<span v-if="a.count > 1" class="text-ink-gray-4">×{{ a.count }}</span>
					</span>
					<button
						v-if="a.page"
						class="shrink-0 text-ink-gray-4 opacity-0 transition-opacity hover:text-ink-gray-8 hover:underline group-hover:opacity-100"
						@click="openPage(a.page)">
						Open
					</button>
				</div>
			</template>
		</div>

		<!-- body text (markdown) -->
		<div
			v-if="message.text && !isPlan"
			class="ai-prose prose prose-sm max-w-none break-words text-p-sm leading-relaxed"
			:class="message.status === 'error' ? 'text-ink-red-6' : 'text-ink-gray-8'"
			v-html="renderMarkdown(message.text)" />

		<!-- outcome of a confirmed/skipped sensitive action -->
		<div
			v-if="message.status === 'action_applied' || message.status === 'action_skipped'"
			class="flex items-center gap-1 text-[11px] text-ink-gray-4">
			<span v-if="message.status === 'action_applied'" class="text-ink-gray-6">✓</span>
			{{ message.status === "action_applied" ? "Applied" : "Skipped" }}
		</div>

		<!-- meta row: revert, matching the editor chat's treatment -->
		<div v-if="message.revertSnapshot && !isRunning" class="flex items-center text-[11px] text-ink-gray-4">
			<button
				class="inline-flex items-center gap-1 transition-colors hover:text-ink-gray-7"
				title="Revert the page to before this AI edit"
				@click="$emit('revert', message)">
				<span class="lucide-rotate-ccw size-3" />
				Revert
			</button>
		</div>

		<!-- the page this turn built/edited, one click away -->
		<button
			v-if="donePage"
			class="flex w-fit items-center gap-2 rounded-lg border border-outline-gray-2 px-3 py-1.5 text-xs text-ink-gray-8 transition-colors hover:border-outline-gray-3 hover:bg-surface-gray-2"
			@click="openPage(donePage.page!)">
			<FeatherIcon name="external-link" class="size-3.5 text-ink-gray-5" />
			Open {{ donePageTitle }} in the editor
		</button>

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
import { renderMarkdown } from "@/components/ai/markdown";
import router from "@/router";
import { Button, FeatherIcon } from "frappe-ui";
import { computed, ref } from "vue";
import TaskGroupCard from "./TaskGroupCard.vue";
import type { ActivityEntry, AgentMessage, BatchState } from "./useAgentChat";

const props = defineProps<{ message: AgentMessage; batch?: BatchState | null; publishing?: boolean }>();
defineEmits<{
	(e: "select-option", option: string): void;
	(e: "approve-plan"): void;
	(e: "confirm", message: AgentMessage, decision: "apply" | "skip"): void;
	(e: "publish", batchId: string): void;
	(e: "revert", message: AgentMessage): void;
}>();

const isPlan = computed(() => props.message.status === "plan_summary" && !!props.message.plan);
const stepsOpen = ref(false);

// Collapse consecutive repeats ("Read block", "Read block", …) into one "×N" line.
const activityDisplay = computed(() => {
	const out: Array<ActivityEntry & { count: number }> = [];
	for (const a of props.message.activity || []) {
		const last = out[out.length - 1];
		if (last && last.summary === a.summary && last.status === a.status) {
			last.count++;
		} else {
			out.push({ ...a, count: 1 });
		}
	}
	return out;
});
const stepCount = computed(() => (props.message.activity || []).length);

const isRunning = computed(() => props.message.status === "running" && !props.message.batchId);
// While running, the single status line prefers the model's narration, then the
// step in flight, then the last finished step.
const workingLine = computed(() => {
	if (props.message.progress) return props.message.progress;
	const acts = props.message.activity || [];
	const current = acts.find((a) => a.status === "running") || acts[acts.length - 1];
	return current?.summary || "Working…";
});

// The page this turn worked on — surfaced as a review link once the turn settles.
const donePage = computed(() => {
	if (!["complete", "action_applied", "action_skipped"].includes(props.message.status)) return null;
	const withPage = (props.message.activity || []).filter((a) => a.page);
	return withPage.length ? withPage[withPage.length - 1] : null;
});
const donePageTitle = computed(() => {
	const named = (props.message.activity || []).find(
		(a) => a.page === donePage.value?.page && a.summary.includes("page: "),
	);
	return named ? named.summary.split("page: ")[1].split(" — ")[0] : "the page";
});

function openPage(pageId: string) {
	router.push({ name: "builder", params: { pageId } });
}
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

<style>
/* Unscoped: v-html markdown children carry no scope attribute. Same tokens as the
   editor chat's .ai-prose (BuilderAIChatPanel) so the two chats read identically. */
.ai-prose {
	--tw-prose-body: var(--ink-gray-8);
	--tw-prose-headings: var(--ink-gray-9);
	--tw-prose-bold: var(--ink-gray-9);
	--tw-prose-code: var(--ink-gray-8);
	--tw-prose-links: var(--ink-gray-9);
	--tw-prose-bullets: var(--ink-gray-4);
	--tw-prose-hr: var(--outline-gray-1);
	--tw-prose-quotes: var(--ink-gray-6);
	--tw-prose-quote-borders: var(--outline-gray-2);
}
.ai-prose p:first-child {
	margin-top: 0;
}
.ai-prose p:last-child {
	margin-bottom: 0;
}
.ai-prose code {
	background: var(--surface-gray-2);
	border-radius: 0.25rem;
	padding: 0.1em 0.35em;
	font-size: 0.8em;
}
.ai-prose code::before,
.ai-prose code::after {
	content: none;
}
.ai-prose pre {
	background: var(--surface-gray-2) !important;
	border-radius: 0.375rem;
}
</style>

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
