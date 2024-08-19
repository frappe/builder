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
				group: 'Builder',
				items: [
					{
						label: 'New Page',
						onClick: () => $router.push({ name: 'builder', params: { pageId: 'new' } }),
						icon: 'plus',
					},
				],
			},
			{
				group: 'Settings',
				items: [
					{
						label: `Switch to ${isDark ? 'light' : 'dark'} mode`,
						onClick: () => toggleDark(),
						icon: isDark ? 'sun' : 'moon',
					},
					{ label: 'Page Settings', onClick: () => $router.push({ name: 'settings' }), icon: 'settings' },
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
import useStore from "@/store";
import { useDark, useToggle } from "@vueuse/core";
import { Dropdown } from "frappe-ui";

const store = useStore();

const isDark = useDark();
const toggleDark = useToggle(isDark);
</script>
