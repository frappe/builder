<template>
	<!-- A page Bob builds off-screen: one line that moves with the build, then its
	     result. The steps and Bob's summary wait behind the chevron. -->
	<div class="w-full">
		<div class="flex min-h-7 items-center gap-2">
			<span class="size-3.5 shrink-0" :class="icon" />
			<template v-if="running">
				<span class="animate-shine shrink-0 text-sm text-ink-gray-7">Building {{ page.title }}</span>
				<span class="min-w-0 truncate text-xs text-ink-gray-5">{{ currentStep }}</span>
			</template>
			<template v-else>
				<span class="min-w-0 flex-1 truncate text-sm text-ink-gray-7">
					{{ page.built ? "Built" : "Couldn't build" }}
					<a
						:href="router.resolve({ name: 'builder', params: { pageId: page.page_id } }).href"
						class="decoration-outline-gray-4 text-ink-gray-8 underline-offset-2 hover:underline"
						@click.prevent="emit('open', page.page_id)">
						{{ page.title }}
					</a>
					<span class="ml-1 text-xs text-ink-gray-5">{{ page.route }}</span>
				</span>
				<button
					v-if="steps.length || text"
					type="button"
					class="flex shrink-0 items-center gap-0.5 text-xs text-ink-gray-5 transition-colors hover:text-ink-gray-8"
					:aria-expanded="open"
					@click="open = !open">
					<span v-if="elapsed" class="tabular-nums">{{ elapsed }}</span>
					<span class="lucide-chevron-right size-3 transition-transform" :class="open && 'rotate-90'" />
				</button>
			</template>
		</div>
		<div
			v-if="open && !running"
			class="mb-1 ml-[7px] mt-1 flex flex-col gap-2 border-l border-outline-gray-2 pl-3">
			<AITurnTimeline v-if="steps.length" :steps="steps" />
			<div
				v-if="text"
				class="ai-prose prose prose-sm max-w-none break-words text-p-sm text-ink-gray-7"
				v-html="renderMarkdown(text)" />
			<button
				v-if="debug"
				type="button"
				class="flex w-fit items-center gap-1 text-p-xs text-ink-gray-4 transition-colors hover:text-ink-gray-7"
				@click="emit('inspect')">
				<span class="lucide-activity size-3" />
				Inspect this build
			</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import AITurnTimeline from "@/components/ai/AITurnTimeline.vue";
import { renderMarkdown } from "@/components/ai/markdown";
import type { BuildPage } from "@/components/ai/pageChanges";
import type { AITurnStep } from "@/components/ai/types";
import { computed, ref } from "vue";
import { useRouter } from "vue-router";

const props = defineProps<{
	page: BuildPage;
	steps: AITurnStep[];
	/** Bob's summary of the build. */
	text?: string;
	running: boolean;
	elapsedMs?: number;
	debug?: boolean;
}>();

const emit = defineEmits<{ open: [pageId: string]; inspect: [] }>();

const router = useRouter();
const open = ref(false);

const icon = computed(() => {
	if (props.running) return "lucide-file-plus text-ink-gray-5";
	return props.page.built ? "lucide-check text-ink-green-6" : "lucide-circle-alert text-ink-red-5";
});

/** What the build is on right now: the running step, else the last one. */
const currentStep = computed(() => {
	const step =
		[...props.steps].reverse().find((s) => s.status === "running") || props.steps[props.steps.length - 1];
	if (!step) return "";
	return step.kind === "thinking" ? "Thinking" : step.summary || "";
});

const elapsed = computed(() => {
	const secs = Math.round((props.elapsedMs || 0) / 1000);
	if (!secs) return "";
	return secs < 60 ? `${secs}s` : `${Math.floor(secs / 60)}m ${secs % 60}s`;
});
</script>
