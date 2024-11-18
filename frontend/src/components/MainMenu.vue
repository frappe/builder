<template>
	<Dropdown
		:options="[
			{
				group: 'Builder',
				hideLabel: true,
				items: [
					{
						label: 'Back to Dashboard',
						onClick: () => $router.push({ name: 'home' }),
						icon: 'arrow-left',
						condition: () => !store.isDemoMode,
					},
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
						condition: () => !store.isDemoMode,
					},
					{
						label: 'Duplicate Page',
						onClick: () => store.duplicatePage(store.activePage as BuilderPage),
						icon: 'copy',
						condition: () => !store.isDemoMode,
					},
					{
						label: `Toggle Theme`,
						onClick: () => toggleDark(),
						icon: isDark ? 'sun' : 'moon',
					},
					{ label: 'Settings', onClick: () => $emit('showSettings'), icon: 'settings' },
					{
						label: 'Apps',
						component: AppsMenu,
						icon: 'grid',
						condition: () => !store.isDemoMode,
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
							if (!store.activePage) return;
							store.deletePage(store.activePage).then(() => {
								$router.push({ name: 'home' });
							});
						},
						icon: 'trash-2',
						condition: () => !store.isDemoMode,
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
import AppsMenu from "@/components/AppsMenu.vue";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { useDark, useToggle } from "@vueuse/core";
import { Dropdown } from "frappe-ui";

const store = useStore();
const isDark = useDark({
	attribute: "data-theme",
});
const toggleDark = useToggle(isDark);
</script>
