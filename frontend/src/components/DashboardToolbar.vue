<template>
	<div
		class="toolbar flex h-12 items-center justify-end border-b-[1px] border-outline-gray-1 bg-surface-base p-2 px-3 py-1">
		<div class="flex gap-2">
			<Button variant="subtle" iconLeft="lucide-sparkles" @click="goBuild">Build with AI</Button>
			<Button
				variant="solid"
				iconLeft="lucide-plus"
				class="bg-surface-gray-10 !text-ink-base hover:bg-surface-gray-9"
				@click="showTemplatesDialog = true">
				New
			</Button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { useDashboardState } from "@/composables/useDashboardState";
import router from "@/router";

const { showTemplatesDialog } = useDashboardState();

function goBuild() {
	router.push({ name: "site-build-new" });
}
</script>
