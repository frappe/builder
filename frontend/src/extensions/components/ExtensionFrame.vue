<template>
	<div class="relative h-full w-full">
		<div v-if="loading" class="absolute inset-0 grid place-items-center bg-surface-base">
			<LoadingIcon class="h-6 w-6 text-ink-gray-5" />
		</div>
		<!-- no allow-same-origin: the opaque origin is the whole isolation guarantee -->
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
import { getExtensionSource, installedExtensions } from "@/data/extensions";
import { createPortChannel, type Dispatcher, type PortChannel } from "frappe-builder-extension-sdk/transport";
import {
	PROTOCOL_VERSION,
	type ConnectMessage,
	type ExtensionSlot,
	type InstalledExtension,
} from "frappe-builder-extension-sdk/types";
import useBuilderStore from "@/stores/builderStore";
import { onBeforeUnmount, ref, watch } from "vue";

/** One document serves every extension and every slot, so it takes no segment. */
const SHELL_URL = "/builder_extension";

const props = defineProps<{
	extension: string;
	slot: ExtensionSlot;
	initialProps?: Record<string, unknown>;
	/** Answers what the frame calls. Named as B2 names it, and not `onRequest`,
	 * which Vue would read as a listener for a `request` event. */
	dispatch?: Dispatcher;
}>();

/**
 * The channel, not the port: `createPortChannel` owns `port.onmessage`, so one
 * port can back only one channel, and this component needs it for theme events.
 */
const emit = defineEmits<{
	connect: [channel: PortChannel];
	/** Names the channel that went away, so a caller can drop it by identity. */
	disconnect: [channel: PortChannel];
	/** The frame ran its slot, or could not load. A frame whose code throws sends neither. */
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

/**
 * Where this frame gets the extension's code.
 *
 * A dev extension names a URL its dev server serves: those modules import each
 * other by relative path, and only a real URL resolves them.
 *
 * An installation has no URL. Every user has their own copy, and a frame sends no
 * session, so no route could tell whose copy it was answering with.
 */
const code = async (): Promise<{ entry: string } | { source: string }> => {
	const extension = installed();
	if (extension.entry) return { entry: extension.entry };
	return { source: await getExtensionSource(extension) };
};

const handshake = async (): Promise<ConnectMessage> => ({
	v: PROTOCOL_VERSION,
	type: "connect",
	slot: props.slot,
	...(await code()),
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
 * Runs on every `load`, so a reloaded frame reconnects. The old channel closes
 * first, which rejects any call left pending against a document that is gone.
 */
const connect = async () => {
	disconnect();
	loading.value = true;
	const pair = new MessageChannel();
	const opening = createPortChannel(pair.port1, props.dispatch);
	channel = opening;
	opening.listen("slot.ready", finishLoading);

	const message = await handshake().catch((error: Error) => {
		console.error(`[builder] could not load "${props.extension}"`, error);
		finishLoading();
		return null;
	});
	// reading the source is a round trip, and the frame may have reloaded while it
	// ran. `connect` would then have replaced this channel with a newer one
	if (!message || channel !== opening) return;

	// "*" is the only target that reaches an opaque origin. The port makes the
	// broadcast safe: it is transferred once, and this is the last window message
	frame.value?.contentWindow?.postMessage(message, "*", [pair.port2]);
	emit("connect", opening);
};

// the handshake carries the theme once, so a later flip needs its own message
watch(
	() => store.isDark,
	() => channel?.emit("theme", theme()),
);

onBeforeUnmount(disconnect);
</script>
