<template>
	<div class="flex flex-col gap-1">
		<OnboardingChoice
			v-if="canClone"
			:title="__('Bring your website')"
			:description="__('Copy your pages, text and images from your current site.')"
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
import { __ } from "@/translation";
import LucideFilePlus from "~icons/lucide/file-plus";
import LucideGlobe from "~icons/lucide/globe";
import LucideLayoutTemplate from "~icons/lucide/layout-template";
import OnboardingChoice from "./OnboardingChoice.vue";

defineProps<{ canClone: boolean }>();
const emit = defineEmits<{ choose: [path: "clone" | "template" | "blank"] }>();
</script>
