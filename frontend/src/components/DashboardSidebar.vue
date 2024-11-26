<template>
	<section class="sticky bottom-0 left-0 top-0 flex w-60 flex-col gap-3 bg-surface-gray-1 p-2 max-lg:hidden">
		<div class="flex flex-col">
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				@click="() => setFolderActive('')"
				:class="{ 'bg-surface-modal text-ink-gray-8 shadow-sm dark:bg-surface-gray-2': !store.activeFolder }">
				<FilesIcon class="size-4"></FilesIcon>
				All Pages
			</span>
			<span class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6" @click="emit('openSettings')">
				<SettingsIcon class="size-4"></SettingsIcon>
				Settings
			</span>
		</div>
		<div class="flex flex-col">
			<div class="flex justify-between p-2 text-base text-ink-gray-6">
				<span>Folders</span>
				<FeatherIcon
					name="plus"
					class="size-4 cursor-pointer hover:text-ink-gray-8"
					@click="showNewFolderDialog = true"></FeatherIcon>
			</div>
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				v-for="project in builderProjectFolder.data"
				:class="{
					'bg-surface-modal text-ink-gray-8 shadow-sm dark:bg-surface-gray-2': isFolderActive(
						project.folder_name,
					),
				}"
				@click="setFolderActive(project.folder_name)">
				<FolderIcon class="size-4"></FolderIcon>
				{{ project.folder_name }}
			</span>
		</div>
		<NewFolder v-model="showNewFolderDialog"></NewFolder>
	</section>
</template>
<script lang="ts" setup>
import FilesIcon from "@/components/Icons/Files.vue";
import FolderIcon from "@/components/Icons/Folder.vue";
import SettingsIcon from "@/components/Icons/SettingsGear.vue";
import NewFolder from "@/components/Modals/NewFolder.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import useStore from "@/store";
import { FeatherIcon } from "frappe-ui";
import { ref } from "vue";

const store = useStore();

const emit = defineEmits(["openSettings", "setActiveFolder"]);

const showNewFolderDialog = ref(false);

const isFolderActive = (folderName: string) => {
	return store.activeFolder === folderName;
};
const setFolderActive = (folderName: string) => {
	store.activeFolder = folderName;
};
</script>
