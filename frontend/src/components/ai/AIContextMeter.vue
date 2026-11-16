<template>
	<Tooltip :text="`${kTokens(usage.used)} of ${kTokens(usage.total)} tokens in context`">
		<span class="flex items-center gap-1 px-1 text-xs tabular-nums" :class="tone">
			<!-- frappe-ui's Progress is a bar; a ring fits the composer row -->
			<svg viewBox="0 0 16 16" class="size-3.5 -rotate-90">
				<circle cx="8" cy="8" r="6" fill="none" stroke="currentColor" stroke-width="2" class="opacity-25" />
				<circle
					cx="8"
					cy="8"
					r="6"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					:stroke-dasharray="`${(Math.min(usage.pct, 100) / 100) * RING} ${RING}`" />
			</svg>
			{{ usage.pct }}%
		</span>
	</Tooltip>
</template>

<script setup lang="ts">
import type { ContextUsage } from "@/components/ai/contextUsage";
import { Tooltip } from "frappe-ui";
import { computed } from "vue";

const props = defineProps<{ usage: ContextUsage }>();

const RING = 2 * Math.PI * 6;
const kTokens = (n: number) => (n >= 1000 ? `${Math.round(n / 1000)}k` : `${n}`);
const tone = computed(() => (props.usage.pct >= 80 ? "text-ink-amber-7" : "text-ink-gray-5"));
</script>
