<template>
	<div class="flex min-h-0 flex-1 flex-col" @keydown.esc.stop="$emit('close')">
		<div class="flex items-center justify-between px-4 pb-2 pt-3">
			<span class="text-sm font-medium text-ink-gray-8">{{ title }}</span>
			<Button variant="ghost" size="sm" icon="lucide-x" tooltip="Close" @click="$emit('close')" />
		</div>
		<div class="no-scrollbar min-h-0 flex-1 overflow-y-auto px-4 pb-4">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
import { Button } from "frappe-ui";

defineProps<{ title: string }>();
defineEmits<{ close: [] }>();
</script>
