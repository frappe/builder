/**
 * The two frame windows that the host shows for an extension.
 */

import { toast } from "frappe-ui";
import type { MethodTable } from "../bridge/permissions";
import { fields, oneOf, refuse, text } from "../bridge/params";
import { createFrameSurface, readDialogSize, readPopoverSize } from "./frameSurface";

const dialog = createFrameSurface("dialog", { readSize: readDialogSize });
const popover = createFrameSurface("popover", { readSize: readPopoverSize });
const toastTypes = ["success", "error", "warning", "info"] as const;

const showToast = (params: unknown) => {
	const values = fields(params);
	const message = text(values.message, "message");
	const type = values.type === undefined ? undefined : oneOf(values.type, toastTypes, "type");

	if (type) return toast[type](message);
	return toast(message);
};

/**
 * Opens a page of this site in a new tab. The frame has no `allow-popups`, so
 * it asks the host. Only this origin: a frame cannot use the editor to open
 * another site, which a user could take for a Builder link.
 */
const openUrl = (params: unknown) => {
	const sent = text(fields(params).url, "url");
	const url = new URL(sent, window.location.origin);
	if (url.origin !== window.location.origin) {
		throw refuse("An extension can open only pages of this site.", "invalid_params");
	}
	window.open(url.href, "_blank", "noopener");
};

/** `ExtensionDialog.vue` and `ExtensionPopover.vue` read this. */
export const openDialogs = dialog.openFrames;
export const openPopovers = popover.openFrames;

export const dismissDialog = dialog.dismiss;
export const dismissPopover = popover.dismiss;

/** The Open button of the details pane opens a window without a frame call. */
export const openDialog = dialog.open;
export const openPopover = popover.open;

export const uiMethods: MethodTable = {
	// the bridge rate limits toasts. They need no permission, because they do not change the editor state
	"ui.toast": { needs: null, run: showToast },
	// a window changes nothing that a user saves, so it needs no permission
	"ui.openDialog": { needs: null, run: dialog.open },
	"ui.closeDialog": { needs: null, run: dialog.close },
	"ui.openPopover": { needs: null, run: popover.open },
	"ui.closePopover": { needs: null, run: popover.close },
	"ui.openUrl": { needs: null, run: openUrl },
};
