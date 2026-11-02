<template>
	<button v-if="trialNotice" @click="builderStore.openBuilderSettings('global_billing')">
		<Badge variant="subtle" :theme="trialNotice.theme" :label="trialNotice.badge" />
	</button>
</template>
<script setup lang="ts">
import { useCloudBilling } from "@/composables/useCloudBilling";
import useBuilderStore from "@/stores/builderStore";
import { Badge } from "frappe-ui";

const builderStore = useBuilderStore();
const { trialNotice } = useCloudBilling();
</script>
