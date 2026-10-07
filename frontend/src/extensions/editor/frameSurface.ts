/**
 * The record keeping that each frame window of the host needs.
 *
 * A dialog and a popover are different only in the window that the host shows
 * around them. One frame opens each of them, and a different frame closes it.
 * The key of both is the extension, and both have the same three endings. So
 * the state is here, one time. `uiMethods.ts` makes one of these for each type.
 *
 * `surfaces/surfaceItems.ts` does the same for the surfaces of an extension.
 */

import { markRaw, reactive } from "vue";
import { bridge } from "../bridge/bridge";
import { fields, optionalText, optionalWholeNumber, refuse } from "../bridge/params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

/**
 * The size that the extension asks for. Both fields are optional. If a field is
 * not set, the host uses its own start size. The user can always change the
 * size. So this is a start value, not a fixed value.
 */
export type FrameSize = { width?: number; height?: number };

/**
 * Reads a size from the data of the open call.
 *
 * Only a surface with a size calls it. A dialog always has the size of the
 * host. So the host ignores a `width` in `ui.openDialog`, as it ignores any
 * other field that it does not use.
 */
const frameSize = (params: unknown): FrameSize => {
	const sent = fields(params);
	return {
		width: optionalWholeNumber(sent.width, "width"),
		height: optionalWholeNumber(sent.height, "height"),
	};
};

export type OpenFrame = {
	title: string;
	/** Set only by a surface with a size. A dialog has none, because nothing reads it. */
	size?: FrameSize;
	/**
	 * Goes to the frame in its connect handshake.
	 *
	 * It is plain, never reactive. The handshake is a `postMessage`, which clones
	 * the data. A Vue proxy cannot be cloned. These values are plain JSON from the
	 * message, and they do not change while the frame is open. So nothing needs to
	 * watch them.
	 */
	props: Record<string, unknown>;
};

/** `sized` lets the extension give the start size of the frame. Only the popover uses it. */
export const createFrameSurface = (kind: string, { sized = false } = {}) => {
	/** The host component reads this. It is reactive, because an open call must show the frame. */
	const open = reactive(new Map<string, OpenFrame>());

	/** Not in the reactive map. Nothing shows a resolver. */
	const waiting = new Map<string, (result: unknown) => void>();

	/** The extensions that already have a teardown hook. So a second open adds no second hook. */
	const hooked = new Set<string>();

	/**
	 * Resolves the waiting call, and removes the frame.
	 *
	 * One function for all three endings: the frame closed itself, the user closed
	 * it, or the extension stopped. A waiting call that never resolves makes a
	 * frame wait forever.
	 */
	const settle = (extension: string, result: unknown) => {
		waiting.get(extension)?.(result);
		waiting.delete(extension);
		open.delete(extension);
	};

	/** The host calls this when the user closes the frame. */
	const dismiss = (extension: string) => settle(extension, undefined);

	const hookTeardown = (extension: string) => {
		if (hooked.has(extension)) return;
		hooked.add(extension);
		bridge.registerTeardown(extension, () => {
			settle(extension, undefined);
			hooked.delete(extension);
		});
	};

	/**
	 * A second call replaces the first. The caller of the first call gets nothing.
	 * It does not wait for a frame that is gone.
	 */
	const start = (params: unknown, extension: InstalledExtension) => {
		const sent = fields(params);
		const frame: OpenFrame = {
			title: optionalText(sent.title, "title") ?? extension.label,
			...(sized && { size: frameSize(sent) }),
			props: markRaw(fields(sent.props)),
		};

		settle(extension.name, undefined);
		open.set(extension.name, frame);
		hookTeardown(extension.name);

		return new Promise((resolve) => waiting.set(extension.name, resolve));
	};

	const finish = (params: unknown, extension: InstalledExtension) => {
		if (!open.has(extension.name)) {
			throw refuse(`"${extension.name}" has no open ${kind} to close.`, "unknown_item");
		}
		settle(extension.name, fields(params).result);
	};

	return { open, start, finish, dismiss };
};
