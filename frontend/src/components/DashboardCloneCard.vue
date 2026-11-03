<template>
	<SidebarCard
		v-if="available && clone && !dismissed"
		class="m-2"
		:theme="failed ? 'red' : 'gray'"
		:title="title"
		:description="description"
		:dismissible="!running"
		@dismiss="dismissedFor = clone.source_url" />
</template>

<script setup lang="ts">
import { useSiteClone } from "@/composables/useSiteClone";
import { __ } from "@/translation";
import { useStorage } from "@vueuse/core";
import { SidebarCard } from "frappe-ui";
import { computed } from "vue";

const { available, clone, done, failed, running, host, latestStep } = useSiteClone();
const dismissedFor = useStorage("builder_clone_card_dismissed", "");
const dismissed = computed(() => !running.value && dismissedFor.value === clone.value?.source_url);

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
</script>
