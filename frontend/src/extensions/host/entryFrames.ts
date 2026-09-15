/**
 * Whether an extension's entry frame has finished its first run.
 *
 * The details pane waits on this before it draws the actions. The entry registers
 * the open target, and an Open button that arrives later moves the buttons beside it.
 *
 * A frame whose entry fails to import, or whose `main` throws, never says it is
 * ready. So the wait has a cap: a broken extension must still show Disable and
 * Uninstall.
 */

import { reactive } from "vue";
import { bridge } from "./bridge";

export const READY_TIMEOUT_MS = 3000;

const readyEntryFrames = reactive(new Set<string>());

export const isEntryFrameReady = (extension: string) => readyEntryFrames.has(extension);

export const markEntryFrameReady = (extension: string) => readyEntryFrames.add(extension);

/**
 * Starts the wait for an entry frame that just connected.
 *
 * A frame whose handshake failed was marked ready without ever connecting, so the
 * mark is cleared here first. Teardown ends the wait, so a remounted frame waits again.
 */
export const waitForEntryFrame = (extension: string) => {
	readyEntryFrames.delete(extension);
	const timer = setTimeout(() => markEntryFrameReady(extension), READY_TIMEOUT_MS);
	bridge.registerTeardown(extension, () => {
		clearTimeout(timer);
		readyEntryFrames.delete(extension);
	});
};
