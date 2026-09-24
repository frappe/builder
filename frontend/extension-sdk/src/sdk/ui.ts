/**
 * The dialog, popover, and toast, from inside a frame.
 *
 * Two frames are involved and neither knows about the other. One frame asks for
 * a dialog and waits. The host opens the dialog slot's document in a new frame,
 * and that frame calls `closeDialog` when it is done. The host resolves the
 * first frame's pending call with whatever the second one passed.
 *
 * A popover works the same way, in the `popover` slot. It is not modal: the user
 * keeps editing while it stands, and drags it where they want it. So a caller
 * that wants an answer awaits it, and a caller that only opens a panel does not.
 *
 * A toast opens no frame and has no result: the host displays it in Builder.
 *
 * The host draws the chrome, and a dialog keeps the host's own dimensions. A
 * popover is a working panel the extension lives in, so it may ask for a size.
 * The user still drags the corner, so the size only seeds the frame.
 */

import { getChannel, getSlotProps } from "./connect";

/** A starting size in pixels. An unset field keeps Builder's own default. */
export type FrameSize = {
	width?: number;
	height?: number;
};

export type FrameOptions = FrameSize & {
	title?: string;
	/** Handed to the document the slot mounts, at its connect handshake. */
	props?: Record<string, unknown>;
};

export type ToastType = "success" | "error" | "warning" | "info";

export type ToastOptions = {
	/** The visual tone. Omit it for Builder's standard message toast. */
	type?: ToastType;
};

const call = (method: string, params?: unknown) => getChannel().call(method, params);

/** Resolves when the dialog closes: with the result, or with nothing if it was dismissed. */
export const openDialog = (options: FrameOptions = {}) => call("ui.openDialog", options);

/** Called by the dialog's own frame. The result travels back to whoever opened it. */
export const closeDialog = (result?: unknown) => call("ui.closeDialog", { result });

/** Resolves when the popover closes. Opening one does not block the editor. */
export const openPopover = (options: FrameOptions = {}) => call("ui.openPopover", options);

/** Called by the popover's own frame, or by any frame that wants it shut. */
export const closePopover = (result?: unknown) => call("ui.closePopover", { result });

/** Displays a notification in Builder, outside the extension frame. */
export const toast = (message: string, options: ToastOptions = {}) => call("ui.toast", { message, ...options });

export const ui = {
	openDialog,
	closeDialog,
	openPopover,
	closePopover,
	toast,
	/** What the open call was made with. Read by the document the slot mounted. */
	props: () => getSlotProps(),
};
