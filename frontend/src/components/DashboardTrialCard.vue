<template>
	<SidebarCard
		v-if="trialNotice && !isTrialCardDismissed"
		class="m-2"
		:theme="trialNotice.theme"
		:title="trialNotice.title"
		:description="trialNotice.description"
		:dismissible="trialNotice.dismissible"
		:action="{ label: trialNotice.actionLabel, onClick: () => emit('openBilling') }"
		@dismiss="dismissTrialCard" />
</template>
<script setup lang="ts">
import { useCloudBilling } from "@/composables/useCloudBilling";
import { SidebarCard } from "frappe-ui";

const emit = defineEmits<{ openBilling: [] }>();
const { trialNotice, isTrialCardDismissed, dismissTrialCard } = useCloudBilling();
</script>
