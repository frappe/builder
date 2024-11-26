<template>
	<router-link
		@click="
			() => {
				posthog.capture('builder_page_opened', { page_name: page.page_name });
			}
		"
		:to="{ name: 'builder', params: { pageId: page.page_name } }">
		<div
			class="group relative flex w-full cursor-pointer flex-col gap-2 rounded-2xl bg-surface-white p-3 hover:bg-surface-gray-2">
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
								{ label: 'Duplicate', onClick: () => store.duplicatePage(page), icon: 'copy' },
								{
									label: 'View in Desk',
									onClick: () => store.openInDesk(page),
									icon: 'arrow-up-right',
								},
								{
									label: 'Move to Folder',
									onClick: () => showFolderSelector(page),
									icon: 'log-out',
								},
							],
						},
						{
							group: 'Delete',
							hideLabel: true,
							items: [{ label: 'Delete', onClick: () => store.deletePage(page), icon: 'trash' }],
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
	<SelectFolder
		v-model="showFolderSelectorDialog"
		:currentFolder="targetPage?.project_folder || ''"
		@folderSelected="
			async (folder) => {
				await webPages.setValue
					.submit({
						name: targetPage?.page_name,
						project_folder: folder,
					})
					.then(() => {
						if (targetPage) {
							targetPage.project_folder = folder;
							store.activeFolder = folder;
						}
					});
				showFolderSelectorDialog = false;
			}
		"></SelectFolder>
</template>
<script setup lang="ts">
import SelectFolder from "@/components/Modals/SelectFolder.vue";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { posthog } from "@/telemetry";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { UseTimeAgo } from "@vueuse/components";
import { Dropdown } from "frappe-ui";
import { ref } from "vue";

const showFolderSelectorDialog = ref(false);
const targetPage = ref<BuilderPage | null>(null);

const store = useStore();

const showFolderSelector = (page: BuilderPage) => {
	targetPage.value = page;
	showFolderSelectorDialog.value = true;
};

defineProps<{
	page: BuilderPage;
}>();
</script>
