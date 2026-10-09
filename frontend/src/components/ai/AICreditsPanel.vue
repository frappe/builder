<template>
	<div class="flex flex-col">
		<p v-if="!providers.length" class="text-p-sm text-ink-gray-5">No providers are connected yet.</p>
		<div
			v-for="group in providers"
			:key="group.provider"
			class="flex items-center gap-2 border-b border-outline-gray-1 py-2.5">
			<span class="text-sm text-ink-gray-8">{{ group.provider }}</span>
			<AIProviderCredits v-if="group.models.some((m) => m.api_base)" :provider="group.provider" detailed />
			<span v-else class="ml-auto text-p-xs text-ink-gray-4">No balance reported</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import AIProviderCredits from "@/components/ai/AIProviderCredits.vue";
import type { AIProvider } from "@/components/ai/types";

defineProps<{ providers: AIProvider[] }>();
</script>
