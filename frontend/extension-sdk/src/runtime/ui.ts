/**
 * The dialog, the popover and the toast, from inside a frame.
 *
 * Two frames take part, and neither knows about the other. One frame asks for
 * a dialog and waits. The host opens the dialog document in a new frame. That
 * frame calls `closeDialog` when it is done. The host then gives its result to
 * the waiting call of the first frame.
 *
 * A popover works the same way, in the `popover` slot. It is not modal. The
 * user can edit while it is open, and can move it. So a caller that needs an
 * answer waits for it. A caller that only opens a panel does not wait.
 *
 * A toast opens no frame and has no result. The host shows it in Builder.
 *
 * The host shows the window around the document. A dialog keeps the size of
 * the host. A popover is a work panel, so it can ask for a size. The user can
 * still change the size.
 */

import { getChannel, getSlotProps } from "./connect";

/** The start size, in pixels. If a field is not set, Builder uses its default. */
export type FrameSize = {
	width?: number;
	height?: number;
};

export type FrameOptions = FrameSize & {
	title?: string;
	/** Goes to the document of the slot, in the connect handshake. */
	props?: Record<string, unknown>;
};

export type ToastType = "success" | "error" | "warning" | "info";

export type ToastOptions = {
	/** The color of the toast. Leave it out for the standard Builder toast. */
	type?: ToastType;
};

const call = (method: string, params?: unknown) => getChannel().call(method, params);

/** Resolves when the dialog closes. It gives the result, or nothing if the user closed the dialog. */
export const openDialog = (options: FrameOptions = {}) => call("ui.openDialog", options);

/** The frame of the dialog calls this. The result goes back to the caller that opened the dialog. */
export const closeDialog = (result?: unknown) => call("ui.closeDialog", { result });

/** Resolves when the popover closes. An open popover does not block the editor. */
export const openPopover = (options: FrameOptions = {}) => call("ui.openPopover", options);

/** The frame of the popover calls this. Any other frame can also call it to close the popover. */
export const closePopover = (result?: unknown) => call("ui.closePopover", { result });

/** Shows a message in Builder, outside the extension frame. */
export const toast = (message: string, options: ToastOptions = {}) => call("ui.toast", { message, ...options });

export const ui = {
	openDialog,
	closeDialog,
	openPopover,
	closePopover,
	toast,
	/** The props of the open call. The document of the slot reads them. */
	props: () => getSlotProps(),
};
