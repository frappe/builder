<template>
	<!--
		The hidden entry frame of each installed extension. It runs main.js
		and shows nothing. So it is display:none. The surfaces mount the
		visible frames of an extension. This component does not.
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

		<!-- part of the editor, not of an extension. A user loads an extension with it -->
		<DevExtensionDialog />

		<!-- one for the whole editor. confirmations.ts keeps a queue, so it asks one question at a time -->
		<ExtensionConfirmDialog />

		<!-- one for each extension. It shows nothing until ui.openDialog -->
		<ExtensionDialog
			v-for="extension in installedExtensions"
			:key="`dialog-${frameKey(extension)}`"
			:extension="extension" />

		<!-- the same, for ui.openPopover. A popover is not modal, so both can be open -->
		<ExtensionPopover
			v-for="extension in installedExtensions"
			:key="`popover-${frameKey(extension)}`"
			:extension="extension" />
	</div>
</template>

<script setup lang="ts">
import DevExtensionDialog from "@/extensions/components/DevExtensionDialog.vue";
import ExtensionDialog from "@/extensions/components/ExtensionDialog.vue";
import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import ExtensionConfirmDialog from "@/extensions/components/ExtensionConfirmDialog.vue";
import ExtensionPopover from "@/extensions/components/ExtensionPopover.vue";
import { INSTALLATION_DOCTYPE, installedExtensions, loadExtensions } from "@/data/extensions";
import { connectExtension, disconnectExtension, dispatcherFor, teardownExtension } from "@/extensions";
import { markEntryFrameReady, waitForEntryFrame } from "@/extensions/bridge/entryFrames";
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
 * The key includes the code of the frame. So a frame mounts again when the
 * code changes. A frame reads its code one time, in the handshake. A key with
 * only the name would keep the old frame.
 *
 * An installation uses its checksum in the key. So a new build starts a new
 * frame. A dev extension has no checksum. It uses the URL of its dev server.
 * So a dev version of an installed extension mounts its frames again.
 *
 * The key also includes the permissions. `dispatcherFor` keeps the record from
 * when it started. Without this, a frame keeps a permission after the user removes it.
 */
const frameKey = (extension: InstalledExtension) =>
	`${extension.name}@${extension.checksum ?? extension.entry}@${extension.permissions.join(",")}`;

// an unmounted frame only closes its channel. The registrations of the
// extension stay. So this code first removes, by name, each extension that
// left the list or that now loads from a different place
watch(installedExtensions, (current, previous) => {
	previous
		?.filter((extension) => !current.some((row) => frameKey(row) === frameKey(extension)))
		.forEach((extension) => teardownExtension(extension.name));
});
</script>
