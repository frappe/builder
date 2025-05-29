<template>
	<section
		class="sticky bottom-0 left-0 top-0 flex w-60 flex-col gap-3 bg-surface-gray-1 p-2 shadow-lg max-lg:hidden">
		<div class="flex flex-col">
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				@click="() => setFolderActive('')"
				:class="{
					'bg-surface-modal text-ink-gray-8 shadow-sm dark:bg-surface-gray-2': !builderStore.activeFolder,
				}">
				<FilesIcon class="size-4"></FilesIcon>
				All Pages
			</span>
			<span class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6" @click="emit('openSettings')">
				<SettingsIcon class="size-4"></SettingsIcon>
				Settings
			</span>
		</div>
		<div class="flex flex-1 flex-col">
			<div class="flex items-center justify-between p-2 text-base text-ink-gray-6">
				<span>Folders</span>
				<BuilderButton
					variant="subtle"
					icon="plus"
					class="size-4 cursor-pointer hover:text-ink-gray-8"
					@click="showNewFolderDialog = true"></BuilderButton>
			</div>
			<span
				class="flex h-8 w-full cursor-pointer items-center justify-between gap-2 rounded p-2 py-1 text-base text-ink-gray-6"
				v-for="project in builderProjectFolder.data"
				:class="{
					'bg-surface-modal text-ink-gray-8 shadow-sm dark:bg-surface-gray-2': isFolderActive(
						project.folder_name,
					),
				}"
				@click="setFolderActive(project.folder_name)">
				<span class="flex flex-1 gap-1">
					<FolderIcon class="size-4"></FolderIcon>
					<EditableSpan
						v-model="project.folder_name"
						:editable="renamingFolder === project.folder_name"
						:onChange="
							async (newName) => {
								await renameFolder(newName, project);
								renamingFolder = '';
							}
						"
						class="w-full">
						{{ project.folder_name }}
					</EditableSpan>
				</span>
				<Dropdown
					placement="right"
					v-if="isFolderActive(project.folder_name)"
					:options="[
						{
							label: 'Rename',
							onClick: () => {
								renamingFolder = project.folder_name;
							},
							icon: 'edit',
						},
						{
							label: 'Delete Folder',
							onClick: () => deleteFolder(project.folder_name),
							icon: 'trash',
						},
					]">
					<template v-slot="{ open }">
						<BuilderButton icon="more-horizontal" size="sm" variant="ghost" @click="open"></BuilderButton>
					</template>
				</Dropdown>
			</span>
		</div>
		<NewFolder v-model="showNewFolderDialog"></NewFolder>
		<TrialBanner v-if="builderStore.isFCSite"></TrialBanner>
	</section>
</template>
<script lang="ts" setup>
import BuilderButton from "@/components/Controls/BuilderButton.vue";
import EditableSpan from "@/components/EditableSpan.vue";
import FilesIcon from "@/components/Icons/Files.vue";
import FolderIcon from "@/components/Icons/Folder.vue";
import SettingsIcon from "@/components/Icons/SettingsGear.vue";
import NewFolder from "@/components/Modals/NewFolder.vue";
import builderProjectFolder from "@/data/builderProjectFolder";
import useBuilderStore from "@/stores/builderStore";
import { BuilderProjectFolder } from "@/types/Builder/BuilderProjectFolder";
import { confirm } from "@/utils/helpers";
import { createResource, Dropdown } from "frappe-ui";
import { TrialBanner } from "frappe-ui/frappe";
import { ref } from "vue";

const builderStore = useBuilderStore();
const renamingFolder = ref("");
const emit = defineEmits(["openSettings"]);
const showNewFolderDialog = ref(false);

const isFolderActive = (folderName: string) => {
	return builderStore.activeFolder === folderName;
};
const setFolderActive = (folderName: string) => {
	builderStore.activeFolder = folderName;
};

const renameFolder = async (newFolderName: string, targetFolder: BuilderProjectFolder) => {
	if (!newFolderName) return;
	return createResource({
		url: "frappe.client.rename_doc",
	})
		.submit({
			doctype: "Builder Project Folder",
			old_name: targetFolder.folder_name,
			new_name: newFolderName,
		})
		.then(() => {
			builderProjectFolder.data = builderProjectFolder.data.map((folder: BuilderProjectFolder) => {
				if (folder.folder_name === builderStore.activeFolder) {
					folder.folder_name = newFolderName;
				}
				return folder;
			});
			setFolderActive(newFolderName);
		});
};

const deleteFolder = async (folderName: string) => {
	const confirmed = await confirm(
		'Are you sure you want to delete this folder? All the pages under this folder will be visible under "All Pages"',
	);
	if (!confirmed) return;
	await createResource({
		url: "builder.api.delete_folder",
		method: "POST",
		params: {
			folder_name: folderName,
		},
		auto: true,
	});
	builderProjectFolder.data = builderProjectFolder.data.filter(
		(folder: BuilderProjectFolder) => folder.folder_name !== folderName,
	);
	setFolderActive("");
};
</script>
