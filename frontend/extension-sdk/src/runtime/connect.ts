/**
 * The frame side of the handshake.
 *
 * Builder sends one message on the window, with a port. After that, all
 * messages use the port. So this listener is necessary only one time.
 */

import { createPortChannel, type PortChannel } from "../shared/transport/createPortChannel";
import { PROTOCOL_VERSION, type ConnectMessage } from "../shared/types";
import { handleRequest } from "./actions";
import { closeSlot, runSlot, setActiveSlot } from "./slots";

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
 * Mounts and unmounts run in order. The host keeps a dialog or popover frame
 * after it closes, and a later open mounts the slot again with its new props.
 * That open can come while the first mount still runs.
 */
let slotTasks: Promise<unknown> = Promise.resolve();

/** A failed task fails for its caller. The queue goes on, so a later open still works. */
const queueSlotTask = (task: () => unknown) => {
	const result = slotTasks.then(task);
	slotTasks = result.catch(() => undefined);
	return result;
};

const reportSlotError = (error: unknown) => console.error("[builder] the slot could not open or close", error);

const mountSlot = (open: PortChannel, props: unknown) =>
	queueSlotTask(async () => {
		slotProps = (props as Record<string, unknown>) ?? {};
		// the props go to the slot document. So a dialog can open with call-time arguments
		await runSlot(slotProps);
		// A loaded iframe document is not sufficient. The entry and the slot can
		// still import modules. The host removes its loader only after this event.
		open.emit("slot.ready");
	});

const start = async (message: ConnectMessage, port: MessagePort) => {
	const open = createPortChannel(port, handleRequest);
	channel = open;
	open.listen("theme", applyTheme);
	open.listen("slot.open", (props) => mountSlot(open, props).catch(reportSlotError));
	open.listen("slot.close", () => queueSlotTask(closeSlot).catch(reportSlotError));
	applyTheme(message.theme);
	setActiveSlot(message.slot);

	// the shell names no extension. The message tells what to run. A real URL
	// lets the entry import its chunks and assets by relative path
	const entry = queueSlotTask(() => import(/* @vite-ignore */ message.entryUrl));
	// queued now, so a reopen during the import mounts after it. An entry that fails is the error to report
	await Promise.all([entry, mountSlot(open, message.props)]);
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
