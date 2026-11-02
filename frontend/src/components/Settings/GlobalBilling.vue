<template>
	<div class="flex flex-col gap-5">
		<Alert
			v-if="trialNotice"
			:theme="trialNotice.theme"
			:title="trialNotice.title"
			:description="trialNotice.description" />
		<ErrorMessage v-if="error" :message="error" />
		<div v-if="billing" class="divide-y divide-outline-gray-1">
			<SettingsRow :title="planTitle" :description="billing.plan?.subtitle">
				<Button
					variant="solid"
					:label="billing.plan && !billing.trial ? __('Change plan') : __('Choose a plan')"
					@click="choosePlan" />
			</SettingsRow>
			<!-- as in the Cloud dialog: a trial has no bill or payment method yet -->
			<template v-if="!billing.trial">
				<SettingsRow :title="__('Estimated this cycle')" :description="billing.estimate.note">
					<span class="text-base-medium text-ink-gray-8">{{ billing.estimate.amount }}</span>
				</SettingsRow>
				<SettingsRow :title="__('Credit')" :description="billing.credit.note">
					<span class="text-base-medium text-ink-gray-8">{{ billing.credit.amount }}</span>
				</SettingsRow>
				<SettingsRow
					:title="__('Payment method')"
					:description="billing.payment_method?.label ?? __('No payment method yet')" />
			</template>
			<SettingsRow
				:title="__('Frappe Cloud account')"
				:description="__('Invoices, payment methods, and the billing email.')">
				<Button
					:label="__('Open')"
					icon-right="lucide-arrow-up-right"
					:href="accountLinks?.billing"
					:disabled="!accountLinks"
					target="_blank" />
			</SettingsRow>
		</div>
		<span v-else-if="!error" class="text-ink-gray-5">{{ __("Loading...") }}</span>
	</div>
</template>
<script setup lang="ts">
import { openPlanPicker, refreshBilling, useCloudBilling } from "@/composables/useCloudBilling";
import { __ } from "@/translation";
import { getAccountUrl, type AccountLinks } from "@frappe/cloud-sdk/api";
import { Alert, Button, ErrorMessage, SettingsRow } from "frappe-ui";
import { computed, inject, onMounted, ref } from "vue";

const { billing, trialNotice } = useCloudBilling();
const closeSettings = inject<(then: () => void) => void>("closeSettings");
const accountLinks = ref<AccountLinks>();
const error = ref("");

const planTitle = computed(() => {
	if (billing.value?.trial) return __("Trial plan");
	const name = billing.value?.plan?.name;
	return name ? __("{0} plan", [name]) : __("No plan yet");
});

onMounted(() => {
	refreshBilling().catch((reason) => (error.value = reason.message));
	getAccountUrl()
		.then((links) => (accountLinks.value = links))
		.catch((reason) => console.error("Could not read the Frappe Cloud links", reason));
});

const choosePlan = () => closeSettings?.(openPlanPicker);
</script>
