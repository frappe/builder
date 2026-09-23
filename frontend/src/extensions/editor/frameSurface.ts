/**
 * The bookkeeping a host-drawn frame surface repeats.
 *
 * A dialog and a popover differ only in the chrome the host draws around them.
 * Both are opened by one frame and closed by another, both are keyed by the
 * extension, and both have the same three endings. So the state lives here once
 * and `uiMethods.ts` makes one of these per kind.
 *
 * `surfaces/surfaceItems.ts` is the same idea for the surfaces an extension
 * registers, and was extracted at its second surface too.
 */

import { markRaw, reactive } from "vue";
import { bridge } from "../host/bridge";
import { fields, optionalText, optionalWholeNumber, refuse } from "../params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

/**
 * What the extension asks the host to draw around it. Both are optional, and an
 * unset one leaves the host's own starting size. The user resizes from
 * there either way, so this is a seed and not a lock.
 */
export type FrameSize = { width?: number; height?: number };

/**
 * Reads a size off whatever the open call sent.
 *
 * Only a sized surface calls it. A dialog is drawn at the host's own size, so a
 * `width` sent to `ui.openDialog` is dropped like any other field it has no use
 * for, rather than kept where nothing would read it.
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
	/** Set only by a sized surface. A dialog carries none, because none is read. */
	size?: FrameSize;
	/**
	 * Travels to the frame at its connect handshake.
	 *
	 * Raw, never reactive. The handshake is a `postMessage`, which clones what it
	 * sends, and a Vue proxy cannot be cloned. These are plain JSON off the wire
	 * and never change while the frame is open, so there is nothing to observe.
	 */
	props: Record<string, unknown>;
};

/** `sized` lets the extension seed the frame's dimensions. Only the popover does. */
export const createFrameSurface = (kind: string, { sized = false } = {}) => {
	/** Read by the host component. Reactive, because opening one has to paint. */
	const open = reactive(new Map<string, OpenFrame>());

	/** Kept out of the reactive map: a resolver is not state anything renders. */
	const waiting = new Map<string, (result: unknown) => void>();

	/** Which extensions already have a teardown hook, so opening twice adds one hook. */
	const hooked = new Set<string>();

	/**
	 * Settles whoever is waiting, and forgets the frame.
	 *
	 * One function for all three endings — the frame closed itself, the user
	 * dismissed it, or the extension was torn down — because a pending call that
	 * never settles is a frame waiting forever.
	 */
	const settle = (extension: string, result: unknown) => {
		waiting.get(extension)?.(result);
		waiting.delete(extension);
		open.delete(extension);
	};

	/** The host does this itself when the user closes it. */
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
	 * A second call replaces the first. The first one's caller is settled
	 * with nothing, rather than left pending against a frame that is gone.
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
