<template>
	<!--
		The host also owns this window. So all extension popovers look the same.
		It is not modal, as a dialog is. It has no backdrop. The editor still works
		behind it, and the user can move it.
		
		The Builder token manager also uses `DraggablePopup`. The move, the resize,
		the position limits and the close button come from there.
	-->
	<DraggablePopup
		v-if="popover"
		:modelValue="true"
		:width="popover.size?.width ?? DEFAULT_WIDTH"
		:height="popover.size?.height ?? DEFAULT_HEIGHT"
		resizable
		placement="top-right"
		:container="body"
		:placementOffsetLeft="24"
		:placementOffsetTop="96"
		@update:modelValue="dismiss"
		@dragging="(value: boolean) => (pointerBusy = value)"
		@resizing="(value: boolean) => (pointerBusy = value)">
		<template #header>
			<span class="truncate font-medium">{{ popover.title }}</span>
		</template>
		<template #content>
			<!-- an iframe takes the pointer events. So it stops events during a drag -->
			<div class="h-full" :class="pointerBusy && 'pointer-events-none'">
				<ExtensionFrame
					:extension="extension.name"
					v-bind="{ slot: 'popover' }"
					:initialProps="popover.props"
					:request-handler="requestHandler"
					@connect="(channel) => connectExtension(extension.name, channel)"
					@disconnect="(channel) => disconnectExtension(extension.name, channel)" />
			</div>
		</template>
	</DraggablePopup>
</template>

<script setup lang="ts">
import DraggablePopup from "@/components/Controls/DraggablePopup.vue";
import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { connectExtension, disconnectExtension, requestHandlerFor } from "@/extensions";
import { dismissPopover, openPopovers } from "@/extensions/editor/uiMethods";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { computed, ref } from "vue";

/** Used when the extension asks for no size. The user can change the size. */
const DEFAULT_WIDTH = 400;
const DEFAULT_HEIGHT = 520;

const props = defineProps<{ extension: InstalledExtension }>();

const popover = computed(() => openPopovers.get(props.extension.name));
const requestHandler = computed(() => requestHandlerFor(props.extension));
const pointerBusy = ref(false);

/** Opens below the toolbar, at the top right. The user can move it. */
const body = document.body;

/** The close button resolves the waiting `openPopover` with nothing, as a dismiss does. */
const dismiss = () => dismissPopover(props.extension.name);
</script>
