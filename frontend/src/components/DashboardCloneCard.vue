<template>
	<SidebarCard
		v-if="available && clone && !dismissed"
		class="m-2 break-words"
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
import { getDomains } from "@frappe/cloud-sdk/api";
import { useStorage } from "@vueuse/core";
import { SidebarCard } from "frappe-ui";
import { computed, ref, watch } from "vue";

const emit = defineEmits<{ openDomains: [] }>();
const { available, clone, done, failed, running, host, latestStep } = useSiteClone();
const dismissedFor = useStorage("builder_clone_card_dismissed", "");
const dismissed = computed(() => !running.value && dismissedFor.value === clone.value?.source_url);
const offerDomain = ref(false);

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
	offerDomain.value ? { label: __("Connect your domain"), onClick: connectDomain } : undefined,
);

function connectDomain() {
	// the domains are read again on the next load, so a site that got one there stops being offered it
	offerDomain.value = false;
	emit("openDomains");
}

function readDomains() {
	getDomains()
		.then(({ domains }) => (offerDomain.value = domains.every((domain) => domain.is_default)))
		.catch((reason) => console.error("Could not read the domains", reason));
}

watch(done, (isDone) => isDone && readDomains(), { immediate: true });
</script>
