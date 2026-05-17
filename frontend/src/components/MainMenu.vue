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
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { triggerCopyEvent } from "@/utils/helpers";
import { useDark, useToggle } from "@vueuse/core";
import { Dropdown } from "frappe-ui";
import { useRouter } from "vue-router";

const pageStore = usePageStore();
const isDark = useDark({
	attribute: "data-theme",
});
const router = useRouter();
const toggleDark = useToggle(isDark);
const canvasStore = useCanvasStore();

const emit = defineEmits(["showSettings", "showShortcuts"]);

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
			{ label: "Back to Dashboard", onClick: () => router.push({ name: "home" }), icon: "lucide-arrow-left" },
		],
	},
	{
		group: "Page",
		hideLabel: true,
		items: [
			{
				label: "New Page",
				onClick: () => router.push({ name: "builder", params: { pageId: "new" } }),
				icon: "lucide-plus",
			},
			{
				label: "Copy Page",
				onClick: handleCopyPage,
				icon: "lucide-clipboard",
				condition: () => Boolean(pageStore.activePage),
			},
			{
				label: "Duplicate Page",
				onClick: () => pageStore.duplicatePage(pageStore.activePage as BuilderPage),
				icon: "lucide-copy",
			},
			{
				label: "Delete Page",
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
				label: `Toggle Theme`,
				onClick: () => toggleDark(),
				icon: isDark ? "lucide-sun" : "lucide-moon",
			},
			{ label: "Settings", onClick: () => emit("showSettings"), icon: "lucide-settings" },
			{ label: "Shortcuts", onClick: () => emit("showShortcuts"), icon: "lucide-command" },
			{
				label: "Help",
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
