<template>
	<Sidebar class="border-r border-outline-gray-1">
		<SidebarHeader title="Builder" :logo="builderLogo" :menuItems="appMenuItems" class="px-1.5" />

		<ScrollArea class="min-h-0 flex-1" viewport-class="px-2 pt-0.5 pb-2">
			<BuilderInput
				class="mb-2"
				type="text"
				:placeholder="__('Search pages')"
				v-model="searchFilter"
				@input="(value: string) => (searchFilter = value)">
				<template #prefix>
					<span class="lucide-search size-4 text-ink-gray-5" aria-hidden="true" />
				</template>
			</BuilderInput>
			<nav>
				<SidebarItem
					icon="lucide-files"
					:label="__('All Pages')"
					:active="!searchFilter && dashboardView === 'all'"
					@click="openDashboardView('all')" />
			</nav>

			<div class="mt-5 flex h-7 items-center justify-between">
				<SidebarLabel>{{ __("Folders") }}</SidebarLabel>
				<Button
					variant="ghost"
					size="sm"
					icon="lucide-plus"
					:aria-label="__('New folder')"
					:tooltip="__('New folder')"
					@click="newFolder" />
			</div>
			<p
				v-if="!builderProjectFolder.data?.length"
				class="mt-0.5 flex h-7 items-center pl-2 text-sm text-ink-gray-5">
				{{ __("No folders yet") }}
			</p>
			<nav class="mt-0.5 space-y-0.5">
				<ContextMenu
					v-for="folder in builderProjectFolder.data"
					:key="folder.folder_name"
					:options="folderMenu(folder)">
					<SidebarItem
						icon="lucide-folder"
						:label="folder.folder_name"
						:active="
							!searchFilter && dashboardView === 'folder' && builderStore.activeFolder === folder.folder_name
						"
						@click="openDashboardView('folder', folder.folder_name)">
						<template #suffix>
							<span class="mr-2 text-sm text-ink-gray-4">
								{{ folderPageCount(folder.folder_name) || "" }}
							</span>
						</template>
					</SidebarItem>
				</ContextMenu>
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
import { useDashboardState } from "@/composables/useDashboardState";
import builderProjectFolder from "@/data/builderProjectFolder";
import useBuilderStore from "@/stores/builderStore";
import { folderMenu, folderPageCount, promptNewFolder } from "@/utils/pageActions";
import { useDark, useToggle } from "@vueuse/core";
import {
	Button,
	ContextMenu,
	createResource,
	Dialog,
	ScrollArea,
	Sidebar,
	SidebarHeader,
	SidebarHeaderProps,
	SidebarItem,
	SidebarLabel,
} from "frappe-ui";
import { TrialBanner } from "@framework/ui/components/TrialBanner";
import { DialogDescription, DialogTitle } from "reka-ui";
import { computed, defineAsyncComponent, h, ref } from "vue";

const BuilderSettings = defineAsyncComponent(() => import("@/components/BuilderSettings.vue"));
const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const builderStore = useBuilderStore();
const { showTemplatesDialog, searchFilter, dashboardView, openDashboardView } = useDashboardState();
// a folder remembered from an older session must not steer new pages from another view
if (dashboardView.value !== "folder") builderStore.activeFolder = "";

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

const appMenuItems = computed<SidebarHeaderProps["menuItems"]>(() => [
	{
		group: "Builder",
		hideLabel: true,
		options: [
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
		options: [
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
		options: [
			{
				label: __("Help"),
				onClick: () => window.open("https://t.me/frappebuilder"),
				icon: "lucide-info",
			},
		],
	},
]);

// a folder made here opens straight away, so the next step is adding pages to it
const newFolder = () => promptNewFolder((folder) => openDashboardView("folder", folder));

const showSettingsDialog = ref(false);
const builderVersion = (window as any).builder_version;
</script>
