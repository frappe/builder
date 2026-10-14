<template>
	<!--
		The host owns the window. So all extension dialogs look the same. Only the
		document inside belongs to the extension. The Builder settings dialog also
		uses `Controls/Dialog.vue`. The backdrop, Escape and the click outside come
		from there.
	-->
	<Dialog
		v-if="dialog"
		:modelValue="true"
		:size="dialog.size?.size ?? 'lg'"
		bare
		@update:modelValue="dismiss">
		<div class="bg-surface-elevation-2 p-5">
			<div class="flex items-center justify-between pb-4">
				<DialogTitle as="h3" class="text-md-semibold text-ink-gray-9">{{ dialog.title }}</DialogTitle>
				<Button icon="lucide-x" label="Close" variant="ghost" @click="dismiss" />
			</div>
			<ExtensionFrame
				:key="dialog.id"
				:extension="extension.name"
				slot="dialog"
				:initialProps="dialog.props"
				background-class="bg-surface-elevation-2"
				:request-handler="requestHandler"
				:style="{ height: `${frameHeight}px` }"
				@connect="(channel) => connectExtension(extension.name, channel)"
				@disconnect="(channel) => disconnectExtension(extension.name, channel)" />
		</div>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { connectExtension, disconnectExtension, requestHandlerFor } from "@/extensions";
import { dismissDialog, openDialogs } from "@/extensions/editor/uiMethods";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { DialogTitle } from "reka-ui";
import { computed } from "vue";

/** The frame height when the extension asks for none. The dialog content scrolls in this frame. */
const DEFAULT_FRAME_HEIGHT = 192;
const MIN_FRAME_HEIGHT = 120;
/** Of the window. The title, the padding and the backdrop around it stay in view. */
const MAX_FRAME_SHARE = 0.75;

const props = defineProps<{ extension: InstalledExtension }>();

const dialog = computed(() => openDialogs.get(props.extension.name));
const frameHeight = computed(() => {
	const asked = dialog.value?.size?.height ?? DEFAULT_FRAME_HEIGHT;
	return Math.min(Math.max(asked, MIN_FRAME_HEIGHT), Math.round(window.innerHeight * MAX_FRAME_SHARE));
});
const requestHandler = computed(() => requestHandlerFor(props.extension));

/**
 * Escape, the close button and a click outside have the same result. The host
 * resolves the waiting `openDialog` with nothing.
 */
const dismiss = () => dismissDialog(props.extension.name);
</script>
