/**
 * The dialog, the popover and the toast, from inside a frame.
 */

import { getChannel, getSlotProps } from "./connect";

/** In pixels. If a field is not set, Builder uses its default. */
export type FrameSize = {
	/** A popover only: the start width. The user can resize a popover. */
	width?: number;
	/** A popover's start height, or a dialog's frame height. Builder caps a dialog at 75% of the window. */
	height?: number;
	/** A dialog only: its width, as a frappe-ui dialog size. The default is "lg". */
	size?: "sm" | "md" | "lg" | "xl" | "2xl" | "3xl" | "4xl" | "5xl" | "6xl" | "7xl";
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

/** Opens a page of this site in a new tab, such as `/blog/hello-world`. Builder refuses another origin. */
export const openUrl = (url: string) => call("ui.openUrl", { url });

/** Shows a message in Builder, outside the extension frame. */
export const toast = (message: string, options: ToastOptions = {}) => call("ui.toast", { message, ...options });

export const ui = {
	openDialog,
	closeDialog,
	openPopover,
	closePopover,
	toast,
	openUrl,
	/** The props of the open call. The document of the slot reads them. */
	props: () => getSlotProps(),
};
