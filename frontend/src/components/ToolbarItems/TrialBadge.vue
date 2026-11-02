<template>
	<button v-if="trialNotice" :disabled="isPlanPickerOpening" @click="openPlanPicker">
		<Badge variant="subtle" :theme="trialNotice.theme" :label="trialNotice.badge" />
	</button>
</template>
<script setup lang="ts">
import { isPlanPickerOpening, openPlanPicker, useCloudBilling } from "@/composables/useCloudBilling";
import { Badge } from "frappe-ui";

const { trialNotice } = useCloudBilling();
</script>
