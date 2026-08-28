<template>
	<Dropdown
		:options="[
			{
				group: 'Actions',
				hideLabel: true,
				items: [
					{
						label: __('Duplicate'),
						onClick: () => pageStore.duplicatePage(props.page),
						icon: 'lucide-copy',
					},
					{
						label: __('View Page'),
						onClick: () => pageStore.openPageInBrowser(props.page),
						icon: 'lucide-globe',
						condition: () => Boolean(props.page.published),
					},
					{
						label: __('Unpublish'),
						onClick: () => pageStore.unpublishPage(props.page),
						icon: 'lucide-globe-x',
						condition: () => Boolean(props.page.published),
					},
					{
						label: __('View in Desk'),
						onClick: () => openInDesk(props.page),
						icon: 'lucide-arrow-up-right',
					},
					{
						label: __('Delete'),
						onClick: () => pageStore.deletePage(props.page),
						icon: 'lucide-trash',
						condition: () => !props.page.is_standard,
					},
				],
			},
		]"
		:size="size"
		:placement="placement">
		<!-- The slot content becomes the dropdown trigger (reka-ui as-child). -->
		<slot />
	</Dropdown>
</template>

<script setup lang="ts">
import { __ } from "@/translation";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { openInDesk } from "@/utils/helpers";
import { Dropdown } from "frappe-ui";

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		page: BuilderPage;
		size?: "xs" | "sm" | "md" | "lg";
		placement?: "left" | "right" | "center";
	}>(),
	{
		size: "md",
		placement: "left",
	},
);
</script>
