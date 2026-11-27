<template>
	<div class="flex flex-col gap-1">
		<OnboardingChoice
			v-if="aiStart.state !== 'hidden'"
			:title="__('Describe your website')"
			:description="aiStartDescription"
			:disabled="aiStart.state === 'spent'"
			@click="emit('choose', 'describe')">
			<template #icon><LucideSparkles class="size-4" /></template>
		</OnboardingChoice>
		<OnboardingChoice
			v-if="canClone"
			:title="__('Bring your website')"
			:description="__('Copy pages, text and images from your website.')"
			@click="emit('choose', 'clone')">
			<template #icon><LucideGlobe class="size-4" /></template>
		</OnboardingChoice>
		<OnboardingChoice
			:title="__('Use a template')"
			:description="__('Pick a design and make it yours.')"
			@click="emit('choose', 'template')">
			<template #icon><LucideLayoutTemplate class="size-4" /></template>
		</OnboardingChoice>
		<OnboardingChoice
			:title="__('Start blank')"
			:description="__('An empty page and a free hand.')"
			@click="emit('choose', 'blank')">
			<template #icon><LucideFilePlus class="size-4" /></template>
		</OnboardingChoice>
	</div>
</template>

<script setup lang="ts">
import type { AIStartOffer } from "@/composables/useAIStart";
import { __ } from "@/translation";
import { computed } from "vue";
import LucideFilePlus from "~icons/lucide/file-plus";
import LucideGlobe from "~icons/lucide/globe";
import LucideLayoutTemplate from "~icons/lucide/layout-template";
import LucideSparkles from "~icons/lucide/sparkles";
import OnboardingChoice from "./OnboardingChoice.vue";

const props = defineProps<{ canClone: boolean; aiStart: AIStartOffer }>();
const emit = defineEmits<{ choose: [path: "describe" | "clone" | "template" | "blank"] }>();

const aiStartDescription = computed(() =>
	props.aiStart.state === "spent"
		? __("Today's AI allowance is used up. It renews at midnight UTC, {0}.", [props.aiStart.resetsIn])
		: __("Say what it's for and watch AI build it."),
);
</script>
