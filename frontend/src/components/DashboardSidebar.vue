<template>
	<section
		class="sticky bottom-0 left-0 top-0 flex min-h-fit w-60 flex-col gap-2 border-r border-outline-gray-1 bg-surface-gray-1 p-1 max-lg:hidden dark:bg-surface-base">
		<div class="flex flex-col">
			<div class="flex gap-2">
				<div class="flex w-full items-center">
					<Dropdown
						:options="[
							{
								group: 'Builder',
								hideLabel: true,
								items: [
									{
										label: '新建页面',
										onClick: () => (showTemplatesDialog = true),
										icon: 'lucide-plus',
									},
								],
							},
							{
								group: 'Options',
								hideLabel: true,
								items: [
									{
										label: '应用',
										icon: 'lucide-grid',
										submenu: appsSubmenu,
									},
									{
										label: '切换主题',
										onClick: () => toggleDark(),
										icon: isDark ? 'lucide-sun' : 'lucide-moon',
									},
									{
										label: '设置',
										onClick: () => (showSettingsDialog = true),
										icon: 'lucide-settings',
									},
								],
							},
							{
								group: 'Help',
								hideLabel: true,
								items: [
									{
										label: '帮助',
										onClick: () => {
											// @ts-ignore
											window.open('https://t.me/frappebuilder');
										},
										icon: 'lucide-info',
									},
								],
							},
						]"
						:offset="8"
						size="sm">
						<template v-slot="{ open }">
							<button
								class="mx-0.5 flex w-full items-center justify-between rounded p-1.5 dark:hover:bg-surface-gray-2"
								:class="{
									'bg-surface-base shadow-sm': open,
								}">
								<div class="flex w-full cursor-pointer items-center gap-2">
									<img src="/builder_logo.png" alt="logo" class="h-7" />
									<h1 class="mt-[2px] text-md font-semibold leading-5 text-gray-800 dark:text-gray-200">
										Builder
									</h1>
								</div>
								<span
									:class="[
										open ? 'lucide-chevron-up' : 'lucide-chevron-down',
										'h-4 w-4 !text-gray-700 dark:!text-gray-200',
									]"
									aria-hidden="true" />
							</button>
						</template>
					</Dropdown>
				</div>
			</div>
		</div>
		<div class="flex flex-1 flex-col p-1">
			<span
				class="flex cursor-pointer gap-2 rounded p-2 text-base text-ink-gray-6"
				@click="() => setFolderActive('')"
				:class="{
					'bg-surface-elevation-2 text-ink-gray-8 shadow-sm dark:bg-surface-gray-2':
						!builderStore.activeFolder,
				}">
				<FilesIcon class="size-4"></FilesIcon>
				<span>全部页面</span>
			</span>
			<span
				class="flex cursor-pointer gap-2 p-2 text-base text-ink-gray-6"
				@click="showSettingsDialog = true">
				<SettingsIcon class="size-4"></SettingsIcon>
				<span>设置</span>
			</span>
			<div class="flex items-center justify-between p-2 pr-0 text-base text-ink-gray-6">
				<span>文件夹</span>
				<Button
					variant="ghost"
					icon="lucide-plus"
					class="size-4 cursor-pointer hover:text-ink-gray-8"
					@click="promptCreateFolder()"></Button>
			</div>
			<div class="flex p-2" v-show="!builderProjectFolder.data?.length">
				<p class="text-sm text-ink-gray-5">暂无文件夹</p>
			</div>
			<span
				class="flex h-8 w-full cursor-pointer items-center justify-between gap-2 rounded p-2 py-1 pr-0 text-base text-ink-gray-6"
				v-for="project in builderProjectFolder.data"
				:class="{
					'bg-surface-elevation-2 text-ink-gray-8 shadow-sm dark:bg-surface-gray-2': isFolderActive(
						project.folder_name,
					),
				}"
				@click="setFolderActive(project.folder_name)">
				<span class="flex flex-1 gap-2 overflow-hidden">
					<span class="lucide-folder size-4" />
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
						class="w-full capitalize">
						{{ project.folder_name }}
					</EditableSpan>
				</span>
				<Button
					v-if="isFolderActive(project.folder_name) && project.is_standard"
					variant="ghost"
					size="sm"
					icon="lucide-info"
					disabled
					tooltip="系统生成的文件夹无法编辑或删除"
					class="cursor-pointer" />
				<Dropdown
					placement="right"
					v-else-if="isFolderActive(project.folder_name)"
					:options="[
						{
							label: '重命名',
							onClick: () => {
								renamingFolder = project.folder_name;
							},
							icon: 'lucide-edit',
						},
						{
							label: '删除文件夹',
							onClick: () => deleteFolder(project.folder_name),
							icon: 'lucide-trash',
						},
					]">
					<template v-slot="{ open }">
						<Button icon="lucide-more-horizontal" size="sm" variant="ghost" @click="open"></Button>
					</template>
				</Dropdown>
			</span>
		</div>
		<p class="mt-2 p-2 text-center text-sm text-ink-gray-4">版本：{{ builderVersion }}</p>
		<TrialBanner v-if="builderStore.isFCSite"></TrialBanner>
	</section>
	<Dialog v-model="showSettingsDialog" :dismissable="false" size="5xl" bare>
		<template #default>
			<DialogTitle class="sr-only">全局 Builder 设置</DialogTitle>
			<DialogDescription class="sr-only">
				配置此 Builder 项目的全局设置。
			</DialogDescription>
			<BuilderSettings @close="showSettingsDialog = false" :onlyGlobal="true" bare />
		</template>
	</Dialog>
</template>
<script lang="ts" setup>
import EditableSpan from "@/components/EditableSpan.vue";
import FilesIcon from "@/components/Icons/Files.vue";
import SettingsIcon from "@/components/Icons/SettingsGear.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { promptCreateFolder } from "@/utils/dialogs";
import builderProjectFolder from "@/data/builderProjectFolder";
import useBuilderStore from "@/stores/builderStore";
import { BuilderProjectFolder } from "@/types/doctypes";
import { confirm } from "@/utils/helpers";
import { useDark, useToggle } from "@vueuse/core";
import { createResource, Dialog, Dropdown } from "frappe-ui";
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
		'确定要删除此文件夹吗？该文件夹下的所有页面将显示在"全部页面"中',
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
