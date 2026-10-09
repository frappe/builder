<template>
	<div
		class="absolute inset-x-0 bottom-full z-10 mb-1.5 overflow-hidden rounded-5 border border-outline-gray-2 bg-surface-base py-1 shadow-lg"
		role="listbox">
		<!-- mousedown, not click: the textarea must keep focus so typing carries on -->
		<button
			v-for="(command, index) in commands"
			:key="command.name"
			role="option"
			:aria-selected="index === activeIndex"
			class="flex w-full items-center gap-2 px-2.5 py-1.5 text-left"
			:class="index === activeIndex ? 'bg-surface-gray-2' : ''"
			@mouseenter="activeIndex = index"
			@mousedown.prevent="$emit('run', command)">
			<span :class="[command.icon, 'size-3.5 shrink-0 text-ink-gray-5']" />
			<span class="shrink-0 text-sm text-ink-gray-8">/{{ command.name }}</span>
			<span class="truncate text-xs text-ink-gray-5">{{ command.description }}</span>
		</button>
	</div>
</template>

<script setup lang="ts">
import type { SlashCommand } from "@/components/ai/slashCommands";

defineProps<{ commands: SlashCommand[] }>();
defineEmits<{ run: [command: SlashCommand] }>();

const activeIndex = defineModel<number>("activeIndex", { required: true });
</script>
