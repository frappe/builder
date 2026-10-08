<template>
	<!-- The hidden entry frame of each extension. It runs main.js. The surfaces mount the visible frames. -->
	<div>
		<div class="hidden" aria-hidden="true">
			<ExtensionFrame
				v-for="extension in installedExtensions"
				:key="frameKey(extension)"
				:extension="extension.name"
				slot="main"
				:request-handler="requestHandlerFor(extension)"
				@connect="(channel) => connectEntryFrame(extension, channel)"
				@disconnect="(channel) => disconnectExtension(extension.name, channel)" />
		</div>

		<!-- The dialog that loads a dev extension. -->
		<DevExtensionDialog />
	</div>
</template>

<script setup lang="ts">
import DevExtensionDialog from "@/extensions/components/DevExtensionDialog.vue";
import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { INSTALLATION_DOCTYPE, installedExtensions, loadExtensions } from "@/data/extensions";
import { connectExtension, disconnectExtension, requestHandlerFor, teardownExtension } from "@/extensions";
import useBuilderStore from "@/stores/builderStore";
import type { PortChannel } from "frappe-builder-extension-sdk/transport";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { onMounted, onUnmounted, watch } from "vue";

const builderStore = useBuilderStore();

const onInstallationListChanged = ({ doctype }: { doctype: string }) => {
	if (doctype === INSTALLATION_DOCTYPE) void loadExtensions();
};

onMounted(() => {
	builderStore.realtime.emit("doctype_subscribe", INSTALLATION_DOCTYPE);
	builderStore.realtime.on("list_update", onInstallationListChanged);
	void loadExtensions();
});

onUnmounted(() => {
	builderStore.realtime.off("list_update", onInstallationListChanged);
	builderStore.realtime.doctype_unsubscribe(INSTALLATION_DOCTYPE);
});

const connectEntryFrame = (extension: InstalledExtension, channel: PortChannel) => {
	teardownExtension(extension.name);
	connectExtension(extension.name, channel);
};

/**
 * The key has the entry URL and the permissions.
 * So a new build or a permission change mounts the frame again.
 */
const frameKey = (extension: InstalledExtension) =>
	`${extension.name}@${extension.entryUrl}@${extension.permissions.join(",")}`;

// An unmounted frame does not remove the items of its extension.
// So remove each extension that left the list or has a new entry URL.
watch(installedExtensions, (current, previous) => {
	previous
		?.filter((extension) => !current.some((row) => frameKey(row) === frameKey(extension)))
		.forEach((extension) => teardownExtension(extension.name));
});
</script>
