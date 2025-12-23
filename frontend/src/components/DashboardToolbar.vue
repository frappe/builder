<template>
	<div
		class="toolbar flex h-12 items-center justify-end border-b-[1px] border-outline-gray-1 bg-surface-white p-2 px-3 py-1">
		<div class="flex gap-2">
			<router-link
				:to="{ name: 'builder', params: { pageId: 'new' } }"
				@click="
					() => {
						posthog.capture('builder_new_page_created');
					}
				">
				<BuilderButton
					variant="solid"
					iconLeft="plus"
					class="bg-surface-gray-7 !text-ink-white hover:bg-surface-gray-6">
					New
				</BuilderButton>
			</router-link>
		</div>
	</div>
</template>

<script setup lang="ts">
import { posthog } from "@/telemetry";
</script>
