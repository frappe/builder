<template>
	<div class="flex flex-col gap-0.5">
		<p v-if="!sessions.length" class="text-p-sm text-ink-gray-5">No earlier chats on this page.</p>
		<button
			v-for="session in sessions"
			:key="session.name"
			class="flex items-center gap-2 rounded-4 px-1.5 py-1.5 text-left hover:bg-surface-gray-2"
			@click="$emit('switch', session.name)">
			<span class="lucide-message-circle size-3.5 shrink-0 text-ink-gray-4" />
			<span class="flex-1 truncate text-sm text-ink-gray-8">{{ session.title || "New chat" }}</span>
			<span v-if="session.name === current" class="lucide-check size-4 shrink-0 text-ink-gray-7" />
		</button>
		<button
			v-if="current"
			class="mt-2 self-start text-xs text-ink-red-6 underline underline-offset-2"
			@click="$emit('delete')">
			Delete current chat
		</button>
	</div>
</template>

<script setup lang="ts">
defineProps<{ sessions: Array<{ name: string; title: string | null }>; current: string }>();
defineEmits<{ switch: [name: string]; delete: [] }>();
</script>
