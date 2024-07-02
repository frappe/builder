<template>
	<div
		class="group relative mr-2 w-full overflow-hidden rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200"
		@click="() => $emit('click', page)">
		<img
			width="250"
			height="140"
			:src="page.preview"
			onerror="this.src='/assets/builder/images/fallback.png'"
			class="w-full overflow-hidden rounded-lg bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
		<div class="flex items-center justify-between border-t-[1px] px-3 dark:border-zinc-800">
			<span class="inline-block max-w-[160px] py-2 text-sm text-gray-700 dark:text-zinc-200">
				<div class="flex items-center gap-1">
					<p class="truncate">
						{{ page.template_name || page.page_title || page.page_name }}
					</p>
				</div>
			</span>
			<router-link
				:key="page.page_name"
				@click.stop="() => $emit('click', null)"
				:to="{ name: 'builder', params: { pageId: page.page_name } }"
				v-if="is_developer_mode">
				<FeatherIcon name="edit" class="h-4 w-4 text-gray-500 hover:text-gray-700"></FeatherIcon>
			</router-link>
		</div>
	</div>
</template>
<script setup lang="ts">
import { BuilderPage } from "@/types/Builder/BuilderPage";

const is_developer_mode = window.is_developer_mode;

defineProps<{
	page: BuilderPage;
}>();
</script>
