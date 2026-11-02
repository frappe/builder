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
import type { ChatMessage } from "./types";

const props = defineProps<{ message: ChatMessage; hasContent: boolean }>();
defineEmits<{ select: [suggestion: { label: string; prompt: string }] }>();
const dismissed = ref(false);
const suggestions = computed(() => {
	if (props.message.role !== "assistant" || props.message.metadata?.status !== "complete") return [];
	if (!props.hasContent)
		return [
			{
				label: "Explore a direction",
				prompt:
					"Help me find a visual direction. Use what you know about my project and ask about any important gaps, then show me a few previews.",
			},
			{
				label: "Add my content",
				prompt: "Help me organize my real content for this page. What should I provide next?",
			},
			{
				label: "Start building",
				prompt:
					"Start building from the brief we have. Ask only about important missing details and use no invented business facts.",
			},
		];
	const text = props.message.content;
	const options = [];
	if (/\b(contact|email|e-mail)\b/i.test(text))
		options.push({
			label: "Add social links",
			prompt:
				"Help me add my social or professional links near the contact information. Ask me for the real URLs before adding them.",
		});
	if (/\b(developer|portfolio|projects?)\b/i.test(text))
		options.push({
			label: "Show my work",
			prompt:
				"Help me add selected projects to this page. Ask for the real project details, links and images you need, and match the current design.",
		});
	if (/\b(images?|photos?|imagery)\b/i.test(text))
		options.push({
			label: "Explore imagery",
			prompt:
				"Show me a few image options that suit this page and its purpose, so I can choose before you change anything.",
		});
	options.push(
		{
			label: "Refine the design",
			prompt:
				"Suggest a few focused improvements to the typography, spacing and visual hierarchy of this page. Preserve the direction and content we have chosen.",
		},
		{
			label: "Add a section",
			prompt:
				"Help me decide what section would be useful next for this page and its audience. Ask for any real content you need before building it.",
		},
		{
			label: "Check the page",
			prompt:
				"Check this page at desktop and mobile sizes, including images, links, accessibility and layout. Report concrete issues and what you could not verify.",
		},
	);
	return options.slice(0, 3);
});
</script>
