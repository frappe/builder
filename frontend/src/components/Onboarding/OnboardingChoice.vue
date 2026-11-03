<template>
	<button
		type="button"
		class="flex w-full items-center gap-3 rounded-6 border p-3 text-left transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-outline-gray-3"
		:class="
			selected
				? 'border-outline-gray-4 bg-surface-gray-2'
				: 'border-outline-gray-2 hover:border-outline-gray-3 hover:bg-surface-gray-1'
		"
		v-bind="selected === undefined ? {} : { role: 'radio', 'aria-checked': selected }">
		<span
			v-if="$slots.icon"
			class="grid size-9 shrink-0 place-items-center rounded-5 bg-surface-gray-2 text-ink-gray-6">
			<slot name="icon" />
		</span>
		<span class="flex min-w-0 flex-1 flex-col gap-0.5">
			<span class="text-base font-medium text-ink-gray-8">{{ title }}</span>
			<span class="text-p-sm text-ink-gray-5">{{ description }}</span>
		</span>
		<LucideChevronRight v-if="selected === undefined" class="size-4 shrink-0 text-ink-gray-4" />
	</button>
</template>

<script setup lang="ts">
import LucideChevronRight from "~icons/lucide/chevron-right";

// `selected` left out makes this a navigation row with a chevron; set, it is one radio of a group
defineProps<{ title: string; description: string; selected?: boolean }>();
</script>
