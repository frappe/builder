<template>
	<router-link :to="{ name: 'builder', params: { pageId: page.page_name } }">
		<div
			class="group relative flex w-full cursor-pointer flex-col gap-2 rounded-2xl bg-surface-white p-3"
			:class="{
				'!bg-surface-gray-2': selected,
			}">
			<img
				width="250"
				height="140"
				:src="page.preview"
				onerror="this.src='/assets/builder/images/fallback.png'"
				class="w-full overflow-hidden rounded-md object-cover shadow dark:border dark:border-outline-gray-1" />
			<div class="flex items-center justify-between border-outline-gray-2">
				<span class="inline-block max-w-[160px]">
					<div class="flex items-center gap-1">
						<p class="truncate text-base font-medium text-ink-gray-7 group-hover:text-ink-gray-9">
							{{ page.page_title || page.page_name }}
						</p>
					</div>
					<UseTimeAgo v-slot="{ timeAgo }" :time="page.modified">
						<p class="mt-1 block text-sm text-ink-gray-5 group-hover:text-ink-gray-6">Edited {{ timeAgo }}</p>
					</UseTimeAgo>
				</span>
				<Dropdown
					:options="[
						{
							group: 'Actions',
							hideLabel: true,
							items: [
								{
									label: 'Duplicate',
									onClick: () => pageStore.duplicatePage(page),
									icon: 'copy',
								},
								{
									label: 'View in Desk',
									onClick: () => openInDesk(page),
									icon: 'arrow-up-right',
								},
							],
						},
						{
							group: 'Delete',
							hideLabel: true,
							items: [{ label: 'Delete', onClick: () => pageStore.deletePage(page), icon: 'trash' }],
						},
					]"
					size="xs"
					placement="right">
					<template v-slot="{ open }">
						<BuilderButton
							icon="more-horizontal"
							size="sm"
							variant="subtle"
							class="bg-surface-white !text-ink-gray-5 hover:!text-ink-gray-9"
							@click="open"></BuilderButton>
					</template>
				</Dropdown>
			</div>
		</div>
	</router-link>
</template>
<script setup lang="ts">
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { openInDesk } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Dropdown } from "frappe-ui";

const pageStore = usePageStore();

defineProps<{
	page: BuilderPage;
	selected: boolean;
}>();
</script>
