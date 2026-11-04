<template>
	<PluginDetails v-if="selectedPlugin" :plugin="selectedPlugin" @back="selectedPlugin = null" />
	<PluginList v-else @select="(plugin) => (selectedPlugin = plugin)" />
</template>

<script setup lang="ts">
import PluginDetails from "@/components/LeftPanelTabs/Plugins/PluginDetails.vue";
import PluginList from "@/components/LeftPanelTabs/Plugins/PluginList.vue";
import { installations, reloadInstallations } from "@/data/plugins";
import { useIntervalFn } from "@vueuse/core";
import { computed, onMounted, ref, watch } from "vue";

/**
 * The list and the details of one plugin use the same panel, one at a time.
 * The tab owns only the choice of which one is open.
 */
const selectedPlugin = ref<string | null>(null);

/** A crashed install job sends no event. So the list asks again while a row is installing. */
const isInstalling = computed(() => installations.value.some((row) => row.install_state === "Installing"));
const installPoll = useIntervalFn(reloadInstallations, 5000, { immediate: false });
watch(isInstalling, (installing) => (installing ? installPoll.resume() : installPoll.pause()), {
	immediate: true,
});

onMounted(reloadInstallations);
</script>
