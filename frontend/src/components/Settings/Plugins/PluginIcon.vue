<template>
	<!-- the size of the Users pane's avatars. So a large icon cannot change the row height -->
	<img
		v-if="icon && !icon.startsWith('lucide-')"
		:src="icon"
		class="size-8 shrink-0 rounded-4 object-contain"
		alt=""
		aria-hidden="true" />
	<div v-else class="flex size-8 shrink-0 items-center justify-center rounded-4 bg-surface-gray-2">
		<span class="size-4 text-ink-gray-6" :class="icon || 'lucide-plug'" aria-hidden="true" />
	</div>
</template>

<script setup lang="ts">
/** A plugin's icon file, which fills the tile, or a lucide icon class. With neither, a plug. */
defineProps<{ icon?: string | null }>();
</script>
