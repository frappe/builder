<template>
	<section class="sticky bottom-0 left-0 top-0 flex w-60 flex-col gap-3 bg-surface-gray-1 p-2">
		<div class="flex flex-col">
			<span
				class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6 hover:text-ink-gray-7"
				:class="{
					'text-ink-gray-8': !store.activeFolder,
				}">
				<FilesIcon class="size-4"></FilesIcon>
				All Pages
			</span>
			<span
				class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6 hover:text-ink-gray-7"
				@click="emit('openSettings')">
				<SettingsIcon class="size-4"></SettingsIcon>
				Settings
			</span>
		</div>
		<div class="flex flex-col">
			<span class="p-2 text-base text-ink-gray-6">Folders</span>
			<span
				class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6 hover:text-ink-gray-7"
				v-for="project in builderProjectFolder.data"
				:class="{
					'text-ink-gray-8': isFolderActive(project.folder_name),
				}"
				@click="setFolderActive(project.folder_name)">
				<FolderIcon class="size-4"></FolderIcon>
				{{ project.folder_name }}
			</span>
		</div>
	</section>
</template>
<script lang="ts" setup>
import FilesIcon from "@/components/Icons/Files.vue";
import FolderIcon from "@/components/Icons/Folder.vue";
import SettingsIcon from "@/components/Icons/SettingsGear.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import useStore from "@/store";

const store = useStore();

const emit = defineEmits(["openSettings"]);

const isFolderActive = (folderName: string) => {
	return store.activeFolder === folderName;
};
const setFolderActive = (folderName: string) => {
	store.activeFolder = folderName;
};
</script>
