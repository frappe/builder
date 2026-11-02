<template>
	<SidebarCard
		v-if="trialNotice && !isTrialCardDismissed"
		class="m-2"
		:theme="trialNotice.theme"
		:title="trialNotice.title"
		:description="trialNotice.description"
		:dismissible="trialNotice.dismissible"
		:action="{ label: trialNotice.actionLabel, loading: isPlanPickerOpening, onClick: openPlanPicker }"
		@dismiss="dismissTrialCard" />
</template>
<script setup lang="ts">
import { isPlanPickerOpening, openPlanPicker, useCloudBilling } from "@/composables/useCloudBilling";
import { SidebarCard } from "frappe-ui";

const { trialNotice, isTrialCardDismissed, dismissTrialCard } = useCloudBilling();
</script>
