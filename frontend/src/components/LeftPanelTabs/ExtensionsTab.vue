<template>
	<ExtensionDetails
		v-if="selectedExtension"
		:extension="selectedExtension"
		@back="selectedExtension = null" />
	<ExtensionList v-else @select="(extension) => (selectedExtension = extension)" />
</template>

<script setup lang="ts">
import ExtensionDetails from "@/components/LeftPanelTabs/Extensions/ExtensionDetails.vue";
import ExtensionList from "@/components/LeftPanelTabs/Extensions/ExtensionList.vue";
import { installations, reloadInstallations } from "@/data/extensions";
import { useIntervalFn } from "@vueuse/core";
import { computed, onMounted, ref, watch } from "vue";

/**
 * The list and the details of one extension use the same panel, one at a time.
 * The tab owns only the choice of which one is open.
 */
const selectedExtension = ref<string | null>(null);

/** A crashed install job sends no event. So the list asks again while a row is installing. */
const isInstalling = computed(() => installations.value.some((row) => row.install_state === "Installing"));
const installPoll = useIntervalFn(reloadInstallations, 5000, { immediate: false });
watch(isInstalling, (installing) => (installing ? installPoll.resume() : installPoll.pause()), {
	immediate: true,
});

onMounted(reloadInstallations);
</script>
