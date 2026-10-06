/**
 * The frame side of the handshake.
 *
 * Builder sends one message on the window, with a port. After that, all
 * messages use the port. So this listener is necessary only one time.
 */

import { createPortChannel, type PortChannel } from "../shared/transport/createPortChannel";
import { PROTOCOL_VERSION, type ConnectMessage } from "../shared/types";
import { dispatch } from "./actions";
import { runSlot, setActiveSlot } from "./slots";

/**
 * The frame checks the origin, not the host. Each extension frame sends
 * `origin: "null"`. So a check on the host side cannot tell frames apart.
 *
 * Builder serves this file, so the URL of this file gives the host origin.
 * It also gives the hostname that the user really opened. A value set when
 * the page renders can be wrong.
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

/**
 * Runs the extension code from the location that the host gave.
 *
 * Installed code comes as a Blob. A frame sends no cookie, so no route can
 * check who asks for the code. A Blob URL makes the code a module. The import
 * map still finds the SDK inside it, because the map belongs to the document.
 *
 * The frame makes the Blob URL itself. A Blob URL belongs to the origin that
 * made it. This frame has an opaque origin, so it cannot load a URL from the
 * editor. The new Blob also sets the type that a module script must have.
 *
 * A dev extension keeps its URL. A dev server serves separate modules that
 * import each other by relative path. A Blob gives them no path.
 */
const runEntry = async (message: ConnectMessage) => {
	if (message.source === undefined) {
		if (!message.entry) throw new Error("The connect message carried no extension code");
		await import(/* @vite-ignore */ message.entry);
		return;
	}

	const url = URL.createObjectURL(new Blob([message.source], { type: "text/javascript" }));
	try {
		await import(/* @vite-ignore */ url);
	} finally {
		// the module is loaded. A one-file build imports nothing more
		URL.revokeObjectURL(url);
	}
};

const start = async (message: ConnectMessage, port: MessagePort) => {
	channel = createPortChannel(port, dispatch);
	channel.listen("theme", applyTheme);
	applyTheme(message.theme);
	slotProps = message.props ?? {};
	setActiveSlot(message.slot);

	// the shell names no extension. The message tells what to run
	await runEntry(message);
	// the props go to the slot document. So a dialog can open with call-time arguments
	await runSlot(slotProps);
	// A loaded iframe document is not sufficient. The entry and the slot can
	// still import modules. The host removes its loader only after this event.
	channel.emit("slot.ready");
};

/**
 * Adds the handshake listener when this module loads. A module script runs
 * before the `load` event of the iframe. The host waits for that event.
 * So the message cannot come before this listener exists.
 */
export const listenForHandshake = () => {
	window.addEventListener("message", (message: MessageEvent) => {
		if (message.origin !== HOST_ORIGIN) return;
		if (channel) return; // a port moves only one time, so the handshake occurs one time
		if (!isConnectMessage(message.data) || !message.ports[0]) return;
		// if the entry import fails or the slot fails to mount, show the error.
		// Otherwise the frame fails with no message
		start(message.data, message.ports[0]).catch((error) =>
			console.error(`[builder] the "${message.data.slot}" frame could not start`, error),
		);
	});
};
