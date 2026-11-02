<template>
	<ErrorMessage v-if="error" :message="error" />
	<div v-else>
		<div ref="target" class="isolate" />
		<!-- the Cloud panel ends in 64px of padding: pull the card up to its 16px card gap -->
		<div
			v-if="aiCredits && isFirstScreen"
			class="relative -mt-12 mb-10 mx-10 flex items-end justify-between gap-4 rounded-6 border border-outline-gray-2 p-5">
			<div>
				<p class="text-sm text-ink-gray-5">{{ __("AI credits left") }}</p>
				<p class="mt-2 text-3xl-semibold tabular-nums" :class="BALANCE_INK[creditsTheme(aiCredits)]">
					{{ money(aiCredits.balance) }}
				</p>
			</div>
			<p v-if="aiCredits.spent !== null" class="text-base tabular-nums text-ink-gray-6">
				{{ __("{0} spent", [money(aiCredits.spent)]) }}
			</p>
		</div>
	</div>
</template>
<script setup lang="ts">
import { api, type Credits, creditsTheme, money } from "@/components/ai/commands/shared";
import { refreshBilling } from "@/composables/useCloudBilling";
import { __ } from "@/translation";
import { closeCloudSettings, openCloudSettings } from "@frappe/cloud-sdk";
import { ErrorMessage } from "frappe-ui";
import { onMounted, onUnmounted, ref } from "vue";

const target = ref<HTMLElement>();
const error = ref("");
const aiCredits = ref<Credits | null>(null);
const isFirstScreen = ref(false);
const BALANCE_INK = { gray: "text-ink-gray-9", amber: "text-ink-amber-6", red: "text-ink-red-6" };
let screenWatcher: MutationObserver | undefined;

// the Cloud panel shows its plan card only on its first screen: every flow replaces it
function watchFirstScreen() {
	const root = target.value?.querySelector("fc-cloud-settings")?.shadowRoot;
	if (!root) return;
	const update = () => (isFirstScreen.value = Boolean(root.querySelector("section.grid")));
	screenWatcher = new MutationObserver(update);
	screenWatcher.observe(root, { childList: true, subtree: true });
	update();
}

onMounted(() =>
	openCloudSettings({
		context: window.cloud_settings,
		target: target.value,
		panels: ["billing"],
		theme: "auto",
		// choosing a plan ends the trial, so the card and the badge read the billing again
		onClose: () => refreshBilling().catch((reason) => console.error("Could not read the billing", reason)),
	})
		.then(watchFirstScreen)
		.catch(
			(reason) =>
				(error.value = reason instanceof Error ? reason.message : __("Could not open Cloud Settings")),
		),
);
onMounted(() =>
	api<Credits | null>("builder.ai.api.get_site_ai_credits")
		.then((credits) => (aiCredits.value = credits))
		.catch((reason) => console.error("Could not read the AI credits", reason)),
);
onUnmounted(() => {
	screenWatcher?.disconnect();
	closeCloudSettings();
});
</script>
