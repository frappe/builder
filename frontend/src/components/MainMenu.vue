<template>
	<Dropdown
		:options="[
			{
				group: 'Builder',
				hideLabel: true,
				items: [
					{ label: 'Back to Dashboard', onClick: () => $router.push({ name: 'home' }), icon: 'arrow-left' },
				],
			},
			{
				group: 'Page',
				hideLabel: true,
				items: [
					{
						label: 'New Page',
						onClick: () => $router.push({ name: 'builder', params: { pageId: 'new' } }),
						icon: 'plus',
					},
					{
						label: 'Copy Page',
						onClick: handleCopyPage,
						icon: 'clipboard',
						condition: () => Boolean(pageStore.activePage),
					},
					{
						label: 'Duplicate Page',
						onClick: () => pageStore.duplicatePage(pageStore.activePage as BuilderPage),
						icon: 'copy',
					},
					{
						label: `Toggle Theme`,
						onClick: () => toggleDark(),
						icon: isDark ? 'sun' : 'moon',
					},
					{ label: 'Settings', onClick: () => $emit('showSettings'), icon: 'settings' },

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
			{
				group: 'Delete',
				hideLabel: true,
				items: [
					{
						label: 'Delete Page',
						onClick: () => {
							if (!pageStore.activePage) return;
							pageStore.deletePage(pageStore.activePage).then(() => {
								$router.push({ name: 'home' });
							});
						},
						icon: 'trash-2',
					},
				],
			},
		]"
		size="sm"
		class="flex-1 [&>div>div>div]:w-full"
		placement="right">
		<template v-slot="{ open }">
			<div class="flex cursor-pointer items-center gap-2">
				<img src="/builder_logo.png" alt="logo" class="h-7" />
				<FeatherIcon
					:name="open ? 'chevron-up' : 'chevron-down'"
					class="h-4 w-4 !text-gray-700 dark:!text-gray-200"></FeatherIcon>
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

const pageStore = usePageStore();
const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
const canvasStore = useCanvasStore();

const handleCopyPage = () => {
	if (!pageStore.activePage) return;
	canvasStore.copyEntirePage = true;
	canvasStore.requiresConfirmationForCopyingEntirePage = false;
	triggerCopyEvent();
};
</script>
