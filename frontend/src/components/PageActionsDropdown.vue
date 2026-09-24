<template>
	<Dropdown v-model:open="open" :options="pageMenu(page)" :size="size" :align="align">
		<!-- The slot content becomes the dropdown trigger (reka-ui as-child).
			 `open` goes through so a trigger that only shows on hover can stay put while its menu is up. -->
		<template #default="triggerProps">
			<slot v-bind="triggerProps" />
		</template>
	</Dropdown>
</template>

<script setup lang="ts">
import { BuilderPage } from "@/types/doctypes";
import { pageMenu } from "@/utils/pageActions";
import { Dropdown } from "frappe-ui";

// the card opens this same menu on right-click
const open = defineModel<boolean>("open", { default: false });

withDefaults(
	defineProps<{
		page: BuilderPage;
		size?: "xs" | "sm" | "md" | "lg";
		align?: "start" | "center" | "end";
	}>(),
	{
		size: "md",
		align: "start",
	},
);
</script>
