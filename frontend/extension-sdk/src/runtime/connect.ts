/** The frame side of the handshake. Builder sends one message with a port. All later messages use the port. */

import { createPortChannel, type PortChannel } from "../shared/transport/createPortChannel";
import { PROTOCOL_VERSION, type ConnectMessage } from "../shared/types";
import { handleRequest } from "./actions";
import { runSlot, setActiveSlot } from "./slots";

/**
 * The frame checks the origin of the message. All extension frames have the origin "null".
 * Builder serves this file. So the URL of this file gives the correct host origin.
 */
const HOST_ORIGIN = new URL(import.meta.url).origin;

let channel: PortChannel | null = null;
let slotProps: Record<string, unknown> = {};

export const getChannel = (): PortChannel => {
	if (!channel) throw new Error("The Builder SDK is not connected yet");
	return channel;
};

export const getSlotProps = () => slotProps;

const isConnectMessage = (data: unknown): data is ConnectMessage =>
	typeof data === "object" &&
	data !== null &&
	(data as ConnectMessage).type === "connect" &&
	(data as ConnectMessage).v === PROTOCOL_VERSION;

const applyTheme = (theme: unknown) => document.documentElement.setAttribute("data-theme", String(theme));

const start = async (message: ConnectMessage, port: MessagePort) => {
	channel = createPortChannel(port, handleRequest);
	channel.listen("theme", applyTheme);
	applyTheme(message.theme);
	slotProps = message.props ?? {};
	setActiveSlot(message.slot);

	// A real URL lets the entry import its chunks and assets by relative path.
	await import(/* @vite-ignore */ message.entryUrl);
	// The props go to the slot. So a dialog can open with arguments.
	await runSlot(slotProps);
	// The entry and the slot can still import modules after the iframe loads.
	// The host removes its loader only after this event.
	channel.emit("slot.ready");
};

/** Adds the listener when the module loads. This occurs before the iframe `load` event. */
export const listenForHandshake = () => {
	window.addEventListener("message", (message: MessageEvent) => {
		if (message.origin !== HOST_ORIGIN) return;
		if (channel) return; // a port moves only one time, so the handshake occurs one time
		if (!isConnectMessage(message.data) || !message.ports[0]) return;
		// Show the error if the entry import or the slot mount fails.
		start(message.data, message.ports[0]).catch((error) =>
			console.error(`[builder] the "${message.data.slot}" frame could not start`, error),
		);
	});
};
