<template>
	<!--
		The host owns the window. So all extension dialogs look the same. Only the
		document inside belongs to the extension. The Builder settings dialog also
		uses `Controls/Dialog.vue`. The backdrop, Escape and the click outside come
		from there.
	-->
	<Dialog v-if="dialog" :modelValue="true" size="lg" @update:modelValue="dismiss">
		<template #body>
			<div class="bg-surface-elevation-2 p-5">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-md-semibold text-ink-gray-9">{{ dialog.title }}</h3>
					<Button icon="lucide-x" variant="ghost" @click="dismiss" />
				</div>
				<ExtensionFrame
					:extension="extension.name"
					slot="dialog"
					:initialProps="dialog.props"
					:request-handler="requestHandler"
					:style="{ height: `${FRAME_HEIGHT}px` }"
					@connect="(channel) => connectExtension(extension.name, channel)"
					@disconnect="(channel) => disconnectExtension(extension.name, channel)" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { connectExtension, disconnectExtension, requestHandlerFor } from "@/extensions";
import { dismissDialog, openDialogs } from "@/extensions/editor/uiMethods";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { computed } from "vue";

/** A small area that the host owns. The dialog content scrolls in this frame. */
const FRAME_HEIGHT = 192;

const props = defineProps<{ extension: InstalledExtension }>();

const dialog = computed(() => openDialogs.get(props.extension.name));
const requestHandler = computed(() => requestHandlerFor(props.extension));

/**
 * Escape, the close button and a click outside have the same result. The host
 * resolves the waiting `openDialog` with nothing.
 */
const dismiss = () => dismissDialog(props.extension.name);
</script>
