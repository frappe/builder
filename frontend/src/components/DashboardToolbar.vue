<template>
	<div
		class="toolbar flex h-12 items-center justify-end border-b-[1px] border-outline-gray-1 bg-surface-white p-2 px-3 py-1">
		<div class="flex gap-2">
			<Button
				variant="solid"
				iconLeft="lucide-plus"
				class="bg-surface-gray-7 !text-ink-white hover:bg-surface-gray-6"
				@click="showTemplatesDialog = true">
				New
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDashboardState } from "@/composables/useDashboardState";

const { showTemplatesDialog } = useDashboardState();
</script>
