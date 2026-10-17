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
import { installations, loadExtensions } from "@/data/extensions";
import useBuilderStore from "@/stores/builderStore";
import { useIntervalFn } from "@vueuse/core";
import { toast } from "frappe-ui";
import { computed, onMounted, onUnmounted, ref, watch } from "vue";

/**
 * The list and the details of one extension use the same panel, one at a time.
 * VS Code opens an extension page from its list in the same way. The tab owns
 * only the choice of which one is open.
 */
const selectedExtension = ref<string | null>(null);

const builderStore = useBuilderStore();

/** A Hub install ends in a background job. Reload the list when it ends. */
const onInstallDone = (event: { extension: string; state: "Ready" | "Failed" }) => {
	loadExtensions();
	if (event.state === "Failed") toast.error(`Could not install ${event.extension}`);
	else toast.success(`Installed ${event.extension}`);
};

/** A crashed install job sends no event. So the list asks again while a row is installing. */
const isInstalling = computed(() => installations.value.some((row) => row.install_state === "Installing"));
const installPoll = useIntervalFn(loadExtensions, 5000, { immediate: false });
watch(isInstalling, (installing) => (installing ? installPoll.resume() : installPoll.pause()), {
	immediate: true,
});

onMounted(() => {
	loadExtensions();
	builderStore.realtime.on("builder_extension_install", onInstallDone);
});

onUnmounted(() => {
	builderStore.realtime.off("builder_extension_install", onInstallDone);
});
</script>
