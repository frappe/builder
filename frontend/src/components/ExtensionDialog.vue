<template>
	<!--
		The host owns the chrome, so every extension dialog looks the same and only
		the document inside it belongs to the extension. `Controls/Dialog.vue`
		is what Builder's own settings dialog uses, so the backdrop, Escape and the
		click outside all come from there.
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
					:dispatch="dispatch"
					:style="{ height: `${FRAME_HEIGHT}px` }"
					@connect="(channel) => connectExtension(extension.name, channel)"
					@disconnect="(channel) => disconnectExtension(extension.name, channel)" />
			</div>
		</template>
	</Dialog>
</template>

<script setup lang="ts">
import Dialog from "@/components/Controls/Dialog.vue";
import ExtensionFrame from "@/components/ExtensionFrame.vue";
import { connectExtension, disconnectExtension, dispatcherFor } from "@/extensions";
import { dismissDialog, openDialogs } from "@/extensions/editor/uiMethods";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { computed } from "vue";

/** A compact host-owned canvas. Dialog content scrolls within this frame. */
const FRAME_HEIGHT = 192;

const props = defineProps<{ extension: InstalledExtension }>();

const dialog = computed(() => openDialogs.get(props.extension.name));
const dispatch = computed(() => dispatcherFor(props.extension));

/**
 * Escape, the close button and a click outside all end the same way: the pending
 * `openDialog` resolves with nothing, and the host does that itself.
 */
const dismiss = () => dismissDialog(props.extension.name);
</script>
