<template>
	<!--
		The hidden entry frame of every installed extension. It runs main.js
		and paints nothing, so it is display:none. An extension's visible frames
		are mounted by the surfaces that own them, never here.
	-->
	<div>
		<div class="hidden" aria-hidden="true">
			<ExtensionFrame
				v-for="extension in installedExtensions"
				:key="frameKey(extension)"
				:extension="extension.name"
				slot="main"
				:dispatch="dispatcherFor(extension)"
				@connect="(channel) => connectEntryFrame(extension, channel)"
				@disconnect="(channel) => disconnectExtension(extension.name, channel)"
				@ready="markEntryFrameReady(extension.name)" />
		</div>

		<!-- editor chrome, not an extension's: it is how one is loaded at all -->
		<DevExtensionDialog />

		<!-- one for the whole editor: grants.ts queues, so one question stands at a time -->
		<ExtensionGrantDialog />

		<!-- one per extension, each rendering nothing until ui.openDialog -->
		<ExtensionDialog
			v-for="extension in installedExtensions"
			:key="`dialog-${frameKey(extension)}`"
			:extension="extension" />

		<!-- the same, for ui.openPopover. A popover is not modal, so both can stand -->
		<ExtensionPopover
			v-for="extension in installedExtensions"
			:key="`popover-${frameKey(extension)}`"
			:extension="extension" />
	</div>
</template>

<script setup lang="ts">
import DevExtensionDialog from "@/components/DevExtensionDialog.vue";
import ExtensionDialog from "@/components/ExtensionDialog.vue";
import ExtensionFrame from "@/components/ExtensionFrame.vue";
import ExtensionGrantDialog from "@/components/ExtensionGrantDialog.vue";
import ExtensionPopover from "@/components/ExtensionPopover.vue";
import { INSTALLATION_DOCTYPE, installedExtensions, loadExtensions } from "@/data/extensions";
import { connectExtension, disconnectExtension, dispatcherFor, teardownExtension } from "@/extensions";
import { markEntryFrameReady, waitForEntryFrame } from "@/extensions/host/entryFrames";
import useBuilderStore from "@/stores/builderStore";
import type { PortChannel } from "frappe-builder-extension-sdk/transport";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { getCurrentInstance, onMounted, onUnmounted, watch } from "vue";

const builderStore = useBuilderStore();
const resourceVm = getCurrentInstance()?.proxy;

const onInstallationListChanged = ({ doctype }: { doctype: string }) => {
	if (doctype === INSTALLATION_DOCTYPE) void loadExtensions(resourceVm);
};

onMounted(() => {
	builderStore.realtime.emit("doctype_subscribe", INSTALLATION_DOCTYPE);
	builderStore.realtime.on("list_update", onInstallationListChanged);
	void loadExtensions(resourceVm);
});

onUnmounted(() => {
	builderStore.realtime.off("list_update", onInstallationListChanged);
	builderStore.realtime.doctype_unsubscribe(INSTALLATION_DOCTYPE);
});

const connectEntryFrame = (extension: InstalledExtension, channel: PortChannel) => {
	teardownExtension(extension.name);
	connectExtension(extension.name, channel);
	waitForEntryFrame(extension.name);
};

/**
 * What the frame runs joins the key, so a frame remounts when the code changes.
 * The name alone would keep it, and a frame reads its code once at the handshake.
 *
 * An installation is keyed by its checksum, so a rebuild starts a new frame. A
 * dev extension has no checksum and is keyed by the URL it is served from, so
 * loading a dev version of an installed extension remounts its frames.
 *
 * The grant joins the key too. `dispatcherFor` closes over the record, so a frame
 * that keeps running after the user revokes a capability keeps the old answer.
 */
const frameKey = (extension: InstalledExtension) =>
	`${extension.name}@${extension.checksum ?? extension.entry}@${extension.capabilities.join(",")}`;

// unmounting a frame only closes its channel. What an extension registered
// outlives it, so an extension that left the list, or that is now served from
// somewhere else, is torn down by name first
watch(installedExtensions, (current, previous) => {
	previous
		?.filter((extension) => !current.some((row) => frameKey(row) === frameKey(extension)))
		.forEach((extension) => teardownExtension(extension.name));
});
</script>
