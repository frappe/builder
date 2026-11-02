<template>
	<ErrorMessage v-if="error" :message="error" />
	<div v-else ref="target" class="isolate h-full" />
</template>
<script setup lang="ts">
import { refreshBilling } from "@/composables/useCloudBilling";
import { __ } from "@/translation";
import { closeCloudSettings, openCloudSettings } from "@frappe/cloud-sdk";
import { ErrorMessage } from "frappe-ui";
import { onMounted, onUnmounted, ref } from "vue";

const target = ref<HTMLElement>();
const error = ref("");

onMounted(() =>
	openCloudSettings({
		context: window.cloud_settings,
		target: target.value,
		panels: ["billing"],
		theme: "auto",
		// choosing a plan ends the trial, so the card and the badge read the billing again
		onClose: () => refreshBilling().catch((reason) => console.error("Could not read the billing", reason)),
	}).catch(
		(reason) =>
			(error.value = reason instanceof Error ? reason.message : __("Could not open Cloud Settings")),
	),
);
onUnmounted(closeCloudSettings);
</script>
