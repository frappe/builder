<template>
	<!--
		The host owns the window. So all extension dialogs look the same. Only the
		document inside belongs to the extension. It looks like the frappe-ui dialog.

		It stays after the first open, hidden while closed. A reopen mounts the slot
		in the loaded frame, so the extension does not load again. The frappe-ui
		dialog removes its content on close, which would drop the frame, and moving
		an iframe in the page reloads it.
	-->
	<Teleport v-if="kept" to="body">
		<div
			v-show="dialog"
			class="fixed inset-0 z-50 overflow-y-auto bg-black-overlay-200 dark:bg-black-overlay-700">
			<!-- centered, as the frappe-ui dialog. A tall dialog scrolls -->
			<div class="flex min-h-full items-center justify-center px-4 py-8" @pointerdown.self="dismiss">
				<!-- the role only while open: isDialogOpen() reads it -->
				<div
					:role="dialog ? 'dialog' : undefined"
					aria-modal="true"
					:aria-labelledby="titleId"
					class="w-full overflow-hidden rounded-7 bg-surface-elevation-1 shadow-xl"
					:class="SIZE_CLASSES[kept.size?.size ?? 'lg']">
					<div class="bg-surface-elevation-2 p-5">
						<div class="flex items-center justify-between pb-4">
							<h3 :id="titleId" class="text-md-semibold text-ink-gray-9">{{ kept.title }}</h3>
							<Button ref="closeButton" icon="lucide-x" label="Close" variant="ghost" @click="dismiss" />
						</div>
						<ExtensionFrame
							:extension="extension.name"
							slot="dialog"
							:active="Boolean(dialog)"
							:initialProps="kept.props"
							background-class="bg-surface-elevation-2"
							:request-handler="requestHandler"
							:style="{ height: `${frameHeight}px` }"
							@connect="(channel) => connectExtension(extension.name, channel)"
							@disconnect="(channel) => disconnectExtension(extension.name, channel)" />
					</div>
				</div>
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { connectExtension, disconnectExtension, requestHandlerFor } from "@/extensions";
import type { DialogSize, OpenFrame } from "@/extensions/editor/frameSurface";
import { dismissDialog, openDialogs } from "@/extensions/editor/uiMethods";
import { useEventListener } from "@vueuse/core";
import { Button } from "frappe-ui";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { computed, nextTick, ref, shallowRef, watch } from "vue";
import { onBeforeRouteLeave } from "vue-router";

/** The frame height when the extension asks for none. The dialog content scrolls in this frame. */
const DEFAULT_FRAME_HEIGHT = 192;
const MIN_FRAME_HEIGHT = 120;
/** Of the window. The title, the padding and the backdrop around it stay in view. */
const MAX_FRAME_SHARE = 0.75;

/** The widths of the frappe-ui dialog. Tailwind needs each class written out. */
const SIZE_CLASSES: Record<DialogSize, string> = {
	sm: "max-w-sm",
	md: "max-w-md",
	lg: "max-w-lg",
	xl: "max-w-xl",
	"2xl": "max-w-2xl",
	"3xl": "max-w-3xl",
	"4xl": "max-w-4xl",
	"5xl": "max-w-5xl",
	"6xl": "max-w-6xl",
	"7xl": "max-w-7xl",
};

const props = defineProps<{ extension: InstalledExtension }>();

const dialog = computed(() => openDialogs.get(props.extension.name));
/** The last open. It stays after a close, so the frame does too. */
const kept = shallowRef<OpenFrame | null>(null);
const closeButton = ref<{ $el: HTMLElement } | null>(null);
const titleId = `extension-dialog-${props.extension.name.replace(/\W/g, "-")}`;

const frameHeight = computed(() => {
	const asked = kept.value?.size?.height ?? DEFAULT_FRAME_HEIGHT;
	return Math.min(Math.max(asked, MIN_FRAME_HEIGHT), Math.round(window.innerHeight * MAX_FRAME_SHARE));
});
const requestHandler = computed(() => requestHandlerFor(props.extension));

/**
 * Escape, the close button and a click outside have the same result. The host
 * resolves the waiting `openDialog` with nothing.
 */
const dismiss = () => dismissDialog(props.extension.name);

// focus moves into the dialog, as in the frappe-ui dialog, so editor shortcuts do not act behind it
watch(
	dialog,
	async (open) => {
		if (!open) return;
		kept.value = open;
		await nextTick();
		closeButton.value?.$el.focus();
	},
	{ immediate: true },
);

useEventListener(window, "keydown", (event: KeyboardEvent) => {
	if (dialog.value && event.key === "Escape") dismiss();
});

// the frappe-ui dialog closed on a route change too
onBeforeRouteLeave(() => {
	if (dialog.value) dismiss();
});
</script>
