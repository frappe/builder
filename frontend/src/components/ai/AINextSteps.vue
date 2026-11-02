<template>
	<div v-if="suggestions.length && !dismissed" class="mt-3" role="group" aria-label="Suggested next steps">
		<div class="mb-1.5 flex items-center justify-between">
			<span class="text-p-xs text-ink-gray-5">Try next</span>
			<Button
				variant="ghost"
				size="xs"
				icon="lucide-x"
				aria-label="Dismiss suggestions"
				@click="dismissed = true" />
		</div>
		<div class="flex flex-wrap gap-1.5">
			<Button
				v-for="suggestion in suggestions"
				:key="suggestion.label"
				size="xs"
				variant="outline"
				class="!rounded-full"
				tooltip="Edit this suggestion before sending"
				@click="$emit('select', suggestion)">
				{{ suggestion.label }}
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";
import { computed, ref } from "vue";
import type { ChatMessage, NextStep } from "./types";

const props = defineProps<{ message: ChatMessage }>();
defineEmits<{ select: [suggestion: NextStep] }>();
const dismissed = ref(false);
const suggestions = computed<NextStep[]>(() => {
	if (props.message.role !== "assistant" || props.message.metadata?.status !== "complete") return [];
	const steps = props.message.metadata.nextSteps;
	if (!Array.isArray(steps)) return [];
	return steps
		.filter(
			(step): step is NextStep =>
				typeof step?.label === "string" &&
				typeof step?.prompt === "string" &&
				!!step.label.trim() &&
				!!step.prompt.trim() &&
				step.label.length <= 60 &&
				step.prompt.length <= 600,
		)
		.slice(0, 3);
});
</script>
