<template>
	<Dropdown
		:options="[
			{
				group: 'Actions',
				hideLabel: true,
				items: [
					{
						label: 'Duplicate',
						onClick: () => pageStore.duplicatePage(props.page),
						icon: 'copy',
					},
					{
						label: 'View in Desk',
						onClick: () => openInDesk(props.page),
						icon: 'arrow-up-right',
					},
				],
			},
			{
				group: 'Delete',
				hideLabel: true,
				items: [{ label: 'Delete', onClick: () => pageStore.deletePage(props.page), icon: 'trash' }],
			},
		]"
		:size="size"
		:placement="placement">
		<template v-slot="{ open }">
			<slot :open="open" />
		</template>
	</Dropdown>
</template>

<script setup lang="ts">
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { openInDesk } from "@/utils/helpers";
import { Dropdown } from "frappe-ui";

const pageStore = usePageStore();

const props = withDefaults(
	defineProps<{
		page: BuilderPage;
		size?: "xs" | "sm" | "md" | "lg";
		placement?: "left" | "right" | "top" | "bottom";
	}>(),
	{
		size: "md",
		placement: "bottom",
	},
);
</script>
