<template>
	<Dropdown :options="mainMenuOptions" size="sm" placement="left" :offset="18">
		<template v-slot="{ open }">
			<div class="flex cursor-pointer items-center gap-2">
				<img src="/builder_logo.png" alt="logo" class="h-7" />
				<span
					:class="[
						open ? 'lucide-chevron-up' : 'lucide-chevron-down',
						'h-4 w-4 !text-gray-700 dark:!text-gray-200',
					]"
					aria-hidden="true" />
			</div>
		</template>
	</Dropdown>
</template>
<script setup lang="ts">
import { __ } from "@/translation";
import { useDashboardState } from "@/composables/useDashboardState";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { triggerCopyEvent } from "@/utils/helpers";
import { useDark, useToggle } from "@vueuse/core";
import { Dropdown } from "frappe-ui";
import { useRouter } from "vue-router";

const { showTemplatesDialog } = useDashboardState();
const pageStore = usePageStore();
const isDark = useDark({
	attribute: "data-theme",
});
const router = useRouter();
const toggleDark = useToggle(isDark);
const canvasStore = useCanvasStore();
// a registry item has no parent to emit to, so write the store directly
const builderStore = useBuilderStore();

const handleCopyPage = () => {
	if (!pageStore.activePage) return;
	canvasStore.copyEntirePage = true;
	canvasStore.requiresConfirmationForCopyingEntirePage = false;
	triggerCopyEvent();
};

const mainMenuOptions = [
	{
		group: "Builder",
		hideLabel: true,
		items: [
			{
				label: __("Back to Dashboard"),
				onClick: () => router.push({ name: "home" }),
				icon: "lucide-arrow-left",
			},
		],
	},
	{
		group: "Page",
		hideLabel: true,
		items: [
			{
				label: __("New Page"),
				onClick: () => (showTemplatesDialog.value = true),
				icon: "lucide-plus",
			},
			{
				label: __("Copy Page"),
				onClick: handleCopyPage,
				icon: "lucide-clipboard",
				condition: () => Boolean(pageStore.activePage),
			},
			{
				label: __("Duplicate Page"),
				onClick: () => pageStore.duplicatePage(pageStore.activePage as BuilderPage),
				icon: "lucide-copy",
			},
			{
				label: __("Delete Page"),
				onClick: () => {
					if (!pageStore.activePage) return;
					pageStore.deletePage(pageStore.activePage).then(() => {
						router.push({ name: "home" });
					});
				},
				icon: "lucide-trash-2",
				condition: () => !Boolean(pageStore.activePage?.is_standard),
			},
		],
	},
	{
		group: "Preferences",
		hideLabel: true,
		items: [
			{
				label: __("Toggle Theme"),
				onClick: () => toggleDark(),
				icon: isDark ? "lucide-sun" : "lucide-moon",
			},
			{
				label: __("Settings"),
				onClick: () => (builderStore.showSettingsDialog = true),
				icon: "lucide-settings",
			},
			{
				label: __("Shortcuts"),
				onClick: () => (builderStore.shortcutsModalOpen = true),
				icon: "lucide-command",
			},
			{
				label: __("Help"),
				onClick: () => {
					// @ts-ignore
					window.open("https://t.me/frappebuilder");
				},
				icon: "lucide-info",
			},
		],
	},
];
</script>
