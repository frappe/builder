<template>
	<div class="relative h-full w-full">
		<div v-if="loading" class="absolute inset-0 grid place-items-center bg-surface-base">
			<LoadingIcon class="h-6 w-6 text-ink-gray-5" />
		</div>
		<!-- Do not add allow-same-origin. The opaque origin isolates the frame. -->
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
import {
	createPortChannel,
	type RequestHandler,
	type PortChannel,
} from "frappe-builder-extension-sdk/transport";
import {
	PROTOCOL_VERSION,
	type ConnectMessage,
	type ExtensionSlot,
	type InstalledExtension,
} from "frappe-builder-extension-sdk/types";
import useBuilderStore from "@/stores/builderStore";
import { onBeforeUnmount, ref, watch } from "vue";

/** One page serves all extensions and slots. See builder/www/builder_extension.html. */
const SHELL_URL = "/builder_extension";

const props = defineProps<{
	extension: string;
	slot: ExtensionSlot;
	initialProps?: Record<string, unknown>;
	/** Answers the calls of the frame. Vue reads `onRequest` as an event listener, so do not use that name. */
	requestHandler?: RequestHandler;
}>();

/** Emits the channel, not the port. One port can have only one channel. */
const emit = defineEmits<{
	connect: [channel: PortChannel];
	/** Gives the closed channel, so the caller can remove it. */
	disconnect: [channel: PortChannel];
	/** The frame ran its slot, or it did not load. */
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

/** Runs on each `load`. It closes the old channel and connects again. */
const connect = () => {
	disconnect();
	loading.value = true;
	const pair = new MessageChannel();
	const opening = createPortChannel(pair.port1, props.requestHandler);
	channel = opening;
	opening.listen("slot.ready", finishLoading);

	let message: ConnectMessage;
	try {
		message = handshake();
	} catch (error) {
		console.error(`[builder] could not load "${props.extension}"`, error);
		return finishLoading();
	}

	// Only "*" can reach an opaque origin. The port makes this safe.
	frame.value?.contentWindow?.postMessage(message, "*", [pair.port2]);
	emit("connect", opening);
};

// The handshake sends the theme one time. This sends each later change.
watch(
	() => store.isDark,
	() => channel?.emit("theme", theme()),
);

onBeforeUnmount(disconnect);
</script>
