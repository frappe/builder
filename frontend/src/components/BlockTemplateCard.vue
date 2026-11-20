<template>
	<div
		class="relative flex h-full w-full translate-x-0 translate-y-0 cursor-pointer flex-col items-center justify-center gap-2 overflow-hidden truncate rounded-5 border border-transparent bg-surface-gray-1 p-2 pt-3"
		draggable="true">
		<div class="flex h-4/5 items-center justify-center" :class="{ 'w-14': !wide }">
			<img v-if="preview" :src="preview" alt="" class="pointer-events-none" />
			<Icon v-else-if="icon" :icon="icon" class="size-6 text-ink-gray-5" />
		</div>
		<p class="text-wrap text-center text-sm text-ink-gray-6">{{ label }}</p>
	</div>
</template>
<script setup lang="ts">
import { Icon } from "frappe-ui";
import type { Component } from "vue";

defineProps<{
	label: string;
	preview?: string;
	icon?: string | Component;
	wide?: boolean;
}>();
</script>
