/**
 * True when the entry frame of an extension finished its first run.
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
 * If a handshake failed, the frame got the ready mark with no connection. So
 * this first removes the mark. Teardown ends the wait. So a frame that mounts
 * again waits again.
 */
export const waitForEntryFrame = (extension: string) => {
	readyEntryFrames.delete(extension);
	const timer = setTimeout(() => markEntryFrameReady(extension), READY_TIMEOUT_MS);
	bridge.registerTeardown(extension, () => {
		clearTimeout(timer);
		readyEntryFrames.delete(extension);
	});
};
