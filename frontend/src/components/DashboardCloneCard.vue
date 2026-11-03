<template>
	<SidebarCard
		v-if="available && clone && !dismissed"
		class="m-2"
		:theme="failed ? 'red' : 'gray'"
		:title="title"
		:description="description"
		:action="domainAction"
		:dismissible="!running"
		@dismiss="dismissedFor = clone.source_url" />
</template>

<script setup lang="ts">
import { useSiteClone } from "@/composables/useSiteClone";
import { __ } from "@/translation";
import { closeCloudSettings, getDomains, openCloudSettings } from "@frappe/cloud-sdk";
import { useStorage } from "@vueuse/core";
import { SidebarCard, toast } from "frappe-ui";
import { computed, onUnmounted, ref, watch } from "vue";

const { available, clone, done, failed, running, host, latestStep } = useSiteClone();
const dismissedFor = useStorage("builder_clone_card_dismissed", "");
const dismissed = computed(() => !running.value && dismissedFor.value === clone.value?.source_url);
const hasCustomDomain = ref(true);

const title = computed(() => {
	if (done.value) return __("{0} is in Builder", [host.value]);
	if (failed.value) return __("Couldn't clone {0}", [host.value]);
	return __("Cloning {0}", [host.value]);
});
const description = computed(() => {
	if (done.value) return __("Its pages are in your dashboard, ready to edit.");
	if (failed.value) return clone.value?.error || __("Something went wrong on our side.");
	return latestStep.value || __("Starting…");
});
// "your domain", not the cloned host: a clone of me.substack.com has no domain of its own to bring
const domainAction = computed(() =>
	done.value && !hasCustomDomain.value
		? { label: __("Connect your domain"), onClick: openDomains }
		: undefined,
);

function readDomains() {
	getDomains()
		.then(({ domains }) => (hasCustomDomain.value = domains.some((domain) => !domain.is_default)))
		.catch((reason) => console.error("Could not read the domains", reason));
}

async function openDomains() {
	try {
		await openCloudSettings({
			context: window.cloud_settings,
			panels: ["domains"],
			theme: "auto",
			onClose: readDomains,
		});
	} catch (reason) {
		toast.error(reason instanceof Error ? reason.message : __("Could not open Cloud Settings"));
	}
}

watch(done, (isDone) => isDone && readDomains(), { immediate: true });
onUnmounted(closeCloudSettings);
</script>
