<template>
	<div class="relative h-full w-full">
		<div v-if="loading" class="absolute inset-0 grid place-items-center bg-surface-base">
			<LoadingIcon class="h-6 w-6 text-ink-gray-5" />
		</div>
		<!-- no allow-same-origin. The opaque origin is the only isolation -->
		<iframe
			ref="frame"
			:src="SHELL_URL"
			class="h-full w-full border-0"
			sandbox="allow-scripts allow-forms"
			@load="connect" />
	</div>
</template>

<script setup lang="ts">
import LoadingIcon from "@/components/Icons/Loading.vue";
import { installedExtensions } from "@/data/extensions";
import { createPortChannel, type Dispatcher, type PortChannel } from "frappe-builder-extension-sdk/transport";
import {
	PROTOCOL_VERSION,
	type ConnectMessage,
	type ExtensionSlot,
	type InstalledExtension,
} from "frappe-builder-extension-sdk/types";
import useBuilderStore from "@/stores/builderStore";
import { onBeforeUnmount, ref, watch } from "vue";

/** 
 * One document serves all extensions and all slots. So the URL has no extra segment. 
 * See builder/www/builder_extension.html
 * */
const SHELL_URL = "/builder_extension";

const props = defineProps<{
	extension: string;
	slot: ExtensionSlot;
	initialProps?: Record<string, unknown>;
	/** Answers the calls of the frame. The name is not `onRequest`, because
	 * Vue reads that name as a listener for a `request` event. */
	dispatch?: Dispatcher;
}>();

/**
 * This component emits the channel, not the port. `createPortChannel` owns
 * `port.onmessage`. So one port can have only one channel. This component
 * also needs the channel for theme events.
 */
const emit = defineEmits<{
	connect: [channel: PortChannel];
	/** Names the closed channel. So a caller can find it and remove it. */
	disconnect: [channel: PortChannel];
	/** The frame ran its slot, or it could not load. If the code of the frame fails, no event occurs. */
	ready: [];
}>();

const store = useBuilderStore();
const frame = ref<HTMLIFrameElement | null>(null);
const loading = ref(true);
let channel: PortChannel | null = null;

const finishLoading = () => {
	loading.value = false;
	emit("ready");
};

const theme = () => (store.isDark ? "dark" : "light");

const installed = (): InstalledExtension => {
	const found = installedExtensions.value.find((row) => row.name === props.extension);
	if (!found) throw new Error(`"${props.extension}" is not installed`);
	return found;
};

const handshake = (): ConnectMessage => ({
	v: PROTOCOL_VERSION,
	type: "connect",
	slot: props.slot,
	entryUrl: installed().entryUrl,
	theme: theme(),
	props: props.initialProps,
});

const disconnect = () => {
	if (!channel) return;
	const closing = channel;
	channel = null;
	closing.close();
	emit("disconnect", closing);
};

/**
 * Runs on each `load`. So a reloaded frame connects again. First, the old
 * channel closes. Each pending call to the old document then fails.
 */
const connect = () => {
	disconnect();
	loading.value = true;
	const pair = new MessageChannel();
	const opening = createPortChannel(pair.port1, props.dispatch);
	channel = opening;
	opening.listen("slot.ready", finishLoading);

	let message: ConnectMessage;
	try {
		message = handshake();
	} catch (error) {
		console.error(`[builder] could not load "${props.extension}"`, error);
		return finishLoading();
	}

	// only "*" can reach an opaque origin. The port makes this safe. The port
	// moves only one time, and this is the last message on the window
	frame.value?.contentWindow?.postMessage(message, "*", [pair.port2]);
	emit("connect", opening);
};

// the handshake sends the theme one time. A later theme change needs its own message
watch(
	() => store.isDark,
	() => channel?.emit("theme", theme()),
);

onBeforeUnmount(disconnect);
</script>
