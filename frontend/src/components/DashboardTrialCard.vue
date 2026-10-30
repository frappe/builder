<template>
	<SidebarCard
		v-if="content"
		class="m-2"
		:theme="content.theme"
		:title="content.title"
		:description="content.description"
		:dismissible="content.dismissible"
		:action="{ label: content.actionLabel, loading: opening, onClick: openBilling }"
		@dismiss="dismiss" />
</template>
<script setup lang="ts">
import { useTrialCard } from "@/composables/useTrialCard";
import { SidebarCard } from "frappe-ui";

const { content, opening, openBilling, dismiss } = useTrialCard();
</script>
