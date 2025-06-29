<template>
	<section
		class="sticky bottom-0 left-0 top-0 flex flex-col gap-3 bg-surface-gray-1 p-2 shadow-lg max-lg:hidden"
		:class="[builderStore.showDashboardSidebar ? 'w-60' : 'w-auto']">
		<div class="flex flex-col">
			<div class="mb-2 flex gap-2">
				<Dialog
					v-model="showSettingsDialog"
					style="z-index: 40"
					class="[&>div>div[id^=headlessui-dialog-panel]]:my-3"
					:options="{
						title: 'Settings',
						size: '5xl',
					}">
					<template #body>
						<BuilderSettings @close="showSettingsDialog = false" :onlyGlobal="true"></BuilderSettings>
					</template>
				</Dialog>
				<div class="flex w-full items-center">
					<Dropdown
						:options="[
							{
								group: 'Builder',
								hideLabel: true,
								items: [
									{
										label: 'New Page',
										onClick: () =>
											$router.push({
												name: 'builder',
												params: { pageId: 'new' },
											}),
										icon: 'plus',
									},
								],
							},
							{
								group: 'Options',
								hideLabel: true,
								items: [
									{
										label: 'Apps',
										component: AppsMenu,
										icon: 'grid',
									},
									{
										label: 'Toggle Theme',
										onClick: () => toggleDark(),
										icon: isDark ? 'sun' : 'moon',
									},
									{
										label: 'Settings',
										onClick: () => (showSettingsDialog = true),
										icon: 'settings',
									},
								],
							},
							{
								group: 'Help',
								hideLabel: true,
								items: [
									{
										label: 'Help',
										onClick: () => {
											// @ts-ignore
											window.open('https://t.me/frappebuilder');
										},
										icon: 'info',
									},
								],
							},
						]"
						size="sm"
						class="flex-1 [&>div>div>div]:w-full"
						placement="right">
						<template v-slot="{ open }">
							<div
								class="flex items-center justify-between rounded py-1"
								:class="{
									'!bg-surface-white shadow-sm dark:!bg-surface-gray-2':
										open && builderStore.showDashboardSidebar,
									'!p-2 hover:bg-surface-gray-2': builderStore.showDashboardSidebar,
								}">
								<div
									class="flex w-full cursor-pointer items-center gap-2"
									:class="{
										'justify-center': !builderStore.showDashboardSidebar,
									}">
									<img src="/builder_logo.png" alt="logo" class="h-7" />
									<h1
										class="text-md mt-[2px] font-semibold leading-5 text-gray-800 dark:text-gray-200"
										v-show="builderStore.showDashboardSidebar">
										Builder
									</h1>
								</div>
								<FeatherIcon
									:name="open ? 'chevron-up' : 'chevron-down'"
									class="h-4 w-4 !text-gray-700 dark:!text-gray-200"
									v-show="builderStore.showDashboardSidebar"></FeatherIcon>
							</div>
						</template>
					</Dropdown>
				</div>
			</div>
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				@click="() => setFolderActive('')"
				:class="{
					'bg-surface-modal text-ink-gray-8 shadow-sm dark:bg-surface-gray-2': !builderStore.activeFolder,
				}">
				<FilesIcon class="size-4"></FilesIcon>
				<span v-show="builderStore.showDashboardSidebar">All Pages</span>
			</span>
			<span
				class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6"
				@click="showSettingsDialog = true">
				<SettingsIcon class="size-4"></SettingsIcon>
				<span v-show="builderStore.showDashboardSidebar">Settings</span>
			</span>
		</div>
		<div class="flex flex-1 flex-col">
			<div
				class="flex items-center justify-between p-2 text-base text-ink-gray-6"
				v-show="builderStore.showDashboardSidebar">
				<span>Folders</span>
				<BuilderButton
					variant="subtle"
					icon="plus"
					class="size-4 cursor-pointer hover:text-ink-gray-8"
					@click="showNewFolderDialog = true"></BuilderButton>
			</div>
			<span
				class="flex h-8 w-full cursor-pointer items-center justify-between gap-2 rounded p-2 py-1 text-base text-ink-gray-6"
				v-show="builderStore.showDashboardSidebar"
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
		<div
			class="flex cursor-pointer items-center gap-2 rounded p-2 text-base text-ink-gray-6 hover:bg-surface-gray-2"
			@click="() => (builderStore.showDashboardSidebar = !builderStore.showDashboardSidebar)">
			<FeatherIcon
				:name="builderStore.showDashboardSidebar ? 'chevrons-left' : 'chevrons-right'"
				class="h-4 w-4" />
			<span v-show="builderStore.showDashboardSidebar">Collapse</span>
		</div>
		<NewFolder v-model="showNewFolderDialog"></NewFolder>
		<TrialBanner v-if="builderStore.isFCSite"></TrialBanner>
	</section>
</template>
<script lang="ts" setup>
import AppsMenu from "@/components/AppsMenu.vue";
import BuilderSettings from "@/components/BuilderSettings.vue";
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
import { useDark, useToggle } from "@vueuse/core";
import { createResource, Dialog, Dropdown } from "frappe-ui";
import { TrialBanner } from "frappe-ui/frappe";
import { ref } from "vue";
const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
const renamingFolder = ref("");
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
const showSettingsDialog = ref(false);
</script>
