<template>
	<div class="flex h-full min-h-[200px] flex-col items-center justify-center gap-1 px-4 text-center">
		<p class="text-p-sm text-ink-gray-6">{{ title }}</p>
		<p v-if="hint" class="text-p-xs text-ink-gray-4">{{ hint }}</p>
	</div>
</template>

<script setup lang="ts">
defineProps<{
	title: string;
	hint?: string;
}>();
</script>
