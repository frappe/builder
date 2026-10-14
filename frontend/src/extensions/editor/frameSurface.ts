/**
 * The record keeping that each frame window of the host needs.
 */

import { markRaw, reactive } from "vue";
import { bridge } from "../bridge/bridge";
import { fields, oneOf, optionalText, optionalWholeNumber, refuse } from "../bridge/params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

/**
 * The size that the extension asks for. Every field is optional. If a field is
 * not set, the host uses its own size. A popover takes `width` and `height` as
 * a start size that the user can change. A dialog takes `size`, a width name,
 * and `height`, the height of its frame.
 */
export type FrameSize = { width?: number; height?: number; size?: DialogSize };

/** The widths of a frappe-ui dialog, from narrow to wide. */
export const DIALOG_SIZES = ["sm", "md", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl", "7xl"] as const;
export type DialogSize = (typeof DIALOG_SIZES)[number];

/** A popover: a start width and height, in pixels. */
export const readPopoverSize = (params: unknown): FrameSize => {
	const sent = fields(params);
	return {
		width: optionalWholeNumber(sent.width, "width"),
		height: optionalWholeNumber(sent.height, "height"),
	};
};

/** A dialog: a width name and a frame height. The host caps the height, so a dialog never covers the editor. */
export const readDialogSize = (params: unknown): FrameSize => {
	const sent = fields(params);
	return {
		size: sent.size === undefined ? undefined : oneOf(sent.size, DIALOG_SIZES, "size"),
		height: optionalWholeNumber(sent.height, "height"),
	};
};

export type OpenFrame = {
	/**
	 * New for each open call. The host component keys the frame by it. So a second
	 * open loads a new frame, which gets the new props in its handshake.
	 */
	id: number;
	title: string;
	/** Set only by a surface that reads a size. */
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

/** `readSize` reads the size that this kind of frame takes from the open call. */
export const createFrameSurface = (
	kind: string,
	{ readSize }: { readSize?: (params: unknown) => FrameSize } = {},
) => {
	/** The host component reads this. It is reactive, because an open call must show the frame. */
	const openFrames = reactive(new Map<string, OpenFrame>());

	/** Not in the reactive map. Nothing shows a resolver. */
	const waiting = new Map<string, (result: unknown) => void>();

	/** The extensions that already have a teardown hook. So a second open adds no second hook. */
	const hooked = new Set<string>();

	let opened = 0;

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
		openFrames.delete(extension);
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
	const open = (params: unknown, extension: InstalledExtension) => {
		const sent = fields(params);
		const frame: OpenFrame = {
			id: ++opened,
			title: optionalText(sent.title, "title") ?? extension.label,
			...(readSize && { size: readSize(sent) }),
			props: markRaw(fields(sent.props)),
		};

		settle(extension.name, undefined);
		openFrames.set(extension.name, frame);
		hookTeardown(extension.name);

		return new Promise((resolve) => waiting.set(extension.name, resolve));
	};

	const close = (params: unknown, extension: InstalledExtension) => {
		if (!openFrames.has(extension.name)) {
			throw refuse(`"${extension.name}" has no open ${kind} to close.`, "unknown_item");
		}
		settle(extension.name, fields(params).result);
	};

	return { openFrames, open, close, dismiss };
};
