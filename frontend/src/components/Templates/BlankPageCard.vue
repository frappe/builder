<template>
	<div class="flex w-full flex-col gap-2">
		<button
			class="w-full rounded-lg border border-dashed border-outline-gray-3 p-1.5 text-ink-gray-5 shadow-sm transition-colors duration-150 hover:border-outline-gray-4 hover:bg-surface-gray-1 hover:text-ink-gray-7"
			@click="$emit('click')">
			<div class="flex aspect-video w-full flex-col items-center justify-center gap-2 rounded-md">
				<PlusIcon class="size-5" />
				<span class="text-sm">{{ label }}</span>
			</div>
		</button>
		<div class="px-[2px]">
			<p class="text-sm-medium text-ink-gray-7">&nbsp;</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import PlusIcon from "~icons/lucide/plus";

defineProps<{
	label: string;
}>();

defineEmits(["click"]);
</script>
