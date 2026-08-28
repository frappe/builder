<template>
	<Sidebar class="border-r border-outline-gray-1">
		<SidebarHeader title="Builder" :logo="builderLogo" :menuItems="appMenuItems" class="px-1.5" />

		<ScrollArea class="min-h-0 flex-1" viewport-class="px-2 pt-0.5 pb-2">
			<nav class="space-y-0.5">
				<SidebarItem
					:label="__('All Pages')"
					:active="!builderStore.activeFolder"
					@click="setFolderActive('')">
					<template #prefix><FilesIcon class="size-4" /></template>
				</SidebarItem>
				<SidebarItem :label="__('Settings')" @click="showSettingsDialog = true">
					<template #prefix><SettingsIcon class="size-4" /></template>
				</SidebarItem>
			</nav>

			<div class="mt-5 flex h-7 items-center justify-between">
				<SidebarLabel>{{ __("Folders") }}</SidebarLabel>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-plus text-ink-gray-5"
					:label="__('New folder')"
					@click="promptCreateFolder()" />
			</div>

			<p
				v-if="!builderProjectFolder.data?.length"
				class="mt-0.5 flex h-7 items-center pl-2 text-sm text-ink-gray-5">
				{{ __("No folders yet") }}
			</p>
			<nav class="mt-0.5 space-y-0.5">
				<SidebarItem
					v-for="project in builderProjectFolder.data"
					:key="project.folder_name"
					icon="lucide-folder"
					:label="project.folder_name"
					:active="isFolderActive(project.folder_name)"
					@click="setFolderActive(project.folder_name)">
					<EditableSpan
						v-model="project.folder_name"
						:editable="renamingFolder === project.folder_name"
						:onChange="
							async (newName) => {
								await renameFolder(newName, project);
								renamingFolder = '';
							}
						"
						@blur="renamingFolder = ''"
						class="w-full truncate text-sm capitalize">
						{{ project.folder_name }}
					</EditableSpan>
					<template #suffix>
						<Button
							v-if="isFolderActive(project.folder_name) && project.is_standard"
							variant="ghost"
							size="sm"
							icon="lucide-info"
							disabled
							:tooltip="__('System generated folder cannot be edited or deleted')"
							class="cursor-pointer" />
						<Dropdown
							v-else-if="isFolderActive(project.folder_name)"
							placement="right"
							:options="[
								{
									label: __('Rename'),
									onClick: () => {
										renamingFolder = project.folder_name;
									},
									icon: 'lucide-edit',
								},
								{
									label: __('Delete Folder'),
									onClick: () => deleteFolder(project.folder_name),
									icon: 'lucide-trash',
								},
							]">
							<template v-slot="{ open }">
								<Button icon="lucide-more-horizontal" size="sm" variant="ghost" @click="open" />
							</template>
						</Dropdown>
					</template>
				</SidebarItem>
			</nav>
		</ScrollArea>

		<div class="mt-auto">
			<p class="p-2 text-center text-sm text-ink-gray-4">{{ __("Version") }}: {{ builderVersion }}</p>
			<TrialBanner v-if="builderStore.isFCSite" />
		</div>
	</Sidebar>
	<Dialog v-model="showSettingsDialog" :dismissable="false" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">{{ __("Global Builder Settings") }}</DialogTitle>
			<DialogDescription class="sr-only">
				{{ __("Configure global settings for this builder project.") }}
			</DialogDescription>
			<BuilderSettings @close="showSettingsDialog = false" :onlyGlobal="true" bare />
		</template>
	</Dialog>
</template>
<script lang="ts" setup>
import { __ } from "@/translation";
import builderLogo from "/builder_logo.png";
import EditableSpan from "@/components/EditableSpan.vue";
import FilesIcon from "@/components/Icons/Files.vue";
import SettingsIcon from "@/components/Icons/SettingsGear.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import builderProjectFolder from "@/data/builderProjectFolder";
import useBuilderStore from "@/stores/builderStore";
import { BuilderProjectFolder } from "@/types/doctypes";
import { promptCreateFolder } from "@/utils/dialogs";
import { confirm } from "@/utils/helpers";
import { useDark, useToggle } from "@vueuse/core";
import {
	createResource,
	Dialog,
	Dropdown,
	ScrollArea,
	Sidebar,
	SidebarHeader,
	SidebarHeaderProps,
	SidebarItem,
	SidebarLabel,
} from "frappe-ui";
import { TrialBanner } from "frappe-ui/frappe";
import { DialogDescription, DialogTitle } from "reka-ui";
import { computed, defineAsyncComponent, h, ref } from "vue";

const BuilderSettings = defineAsyncComponent(() => import("@/components/BuilderSettings.vue"));
const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
const { showTemplatesDialog } = useDashboardState();
const renamingFolder = ref("");

const apps = createResource({
	url: "builder.api.get_apps",
	cache: "other_apps",
	auto: true,
});

const appsSubmenu = computed(() => {
	return (apps.data || []).map((app: { route: string; logo: string; title: string }) => ({
		label: app.title,
		icon: h("img", { src: app.logo }),
		onClick: () => window.open(app.route, "_self"),
	}));
});

// grouped options render fine (the header hands them to Dropdown), but its prop
// type only describes a flat list
const appMenuItems = computed(
	() =>
		[
			{
				group: "Builder",
				hideLabel: true,
				items: [
					{
						label: __("New Page"),
						onClick: () => (showTemplatesDialog.value = true),
						icon: "lucide-plus",
					},
				],
			},
			{
				group: "Options",
				hideLabel: true,
				items: [
					{
						label: __("Apps"),
						icon: "lucide-grid",
						submenu: appsSubmenu.value,
					},
					{
						label: __("Toggle Theme"),
						onClick: () => toggleDark(),
						icon: isDark.value ? "lucide-sun" : "lucide-moon",
					},
					{
						label: __("Settings"),
						onClick: () => (showSettingsDialog.value = true),
						icon: "lucide-settings",
					},
				],
			},
			{
				group: "Help",
				hideLabel: true,
				items: [
					{
						label: __("Help"),
						onClick: () => window.open("https://t.me/frappebuilder"),
						icon: "lucide-info",
					},
				],
			},
		] as unknown as SidebarHeaderProps["menuItems"],
);

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
			builderProjectFolder.data = (builderProjectFolder.data ?? []).map((folder: BuilderProjectFolder) => {
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
		__(
			'Are you sure you want to delete this folder? All the pages under this folder will be visible under "All Pages"',
		),
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
	builderProjectFolder.data = (builderProjectFolder.data ?? []).filter(
		(folder: BuilderProjectFolder) => folder.folder_name !== folderName,
	);
	setFolderActive("");
};
const showSettingsDialog = ref(false);
const builderVersion = (window as any).builder_version;
</script>
