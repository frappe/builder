<template>
	<ExtensionDetails v-if="selectedExtension" :extension="selectedExtension" @back="selectedExtension = null" />
	<ExtensionList v-else @select="(extension) => (selectedExtension = extension)" />
</template>

<script setup lang="ts">
import ExtensionDetails from "@/components/LeftPanelTabs/Extensions/ExtensionDetails.vue";
import ExtensionList from "@/components/LeftPanelTabs/Extensions/ExtensionList.vue";
import { loadExtensions } from "@/data/extensions";
import useBuilderStore from "@/stores/builderStore";
import { toast } from "frappe-ui";
import { onMounted, onUnmounted, ref } from "vue";

/**
 * The list and one extension's details are the same panel, one at a time, the way
 * VS Code opens an extension page from its list. The tab owns which one is open
 * and nothing else.
 */
const selectedExtension = ref<string | null>(null);

const builderStore = useBuilderStore();

/** A Hub install finishes in a background job. Reload the list when it lands. */
const onInstallDone = (event: { extension: string; state: "Ready" | "Failed" }) => {
	loadExtensions();
	if (event.state === "Failed") toast.error(`Could not install ${event.extension}`);
	else toast.success(`Installed ${event.extension}`);
};

onMounted(() => {
	loadExtensions();
	builderStore.realtime.on("builder_extension_install", onInstallDone);
});

onUnmounted(() => {
	builderStore.realtime.off("builder_extension_install", onInstallDone);
});
</script>
