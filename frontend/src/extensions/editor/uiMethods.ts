/**
 * The two frame windows that the host shows for an extension.
 *
 * The host owns the window. So all extension dialogs and popovers look the
 * same. The extension owns only the document inside.
 *
 * `open` and `close` come on the ports of different frames. One frame asks,
 * and the frame that the host opens answers. The host cannot know which frame
 * called. So the key is the extension, because an extension has only one of
 * each at a time.
 *
 * A dialog is modal and covers the editor. A popover is beside the editor, and
 * the user can edit while it is open. Neither needs a permission. Both end in
 * the same way, and `frameSurface.ts` has that code.
 */

import { toast } from "frappe-ui";
import type { MethodTable } from "../bridge/permissions";
import { fields, oneOf, text } from "../bridge/params";
import { createFrameSurface } from "./frameSurface";

const dialog = createFrameSurface("dialog");
const popover = createFrameSurface("popover", { sized: true });
const toastTypes = ["success", "error", "warning", "info"] as const;

const showToast = (params: unknown) => {
	const values = fields(params);
	const message = text(values.message, "message");
	const type = values.type === undefined ? undefined : oneOf(values.type, toastTypes, "type");

	if (type) return toast[type](message);
	return toast(message);
};

/** `ExtensionDialog.vue` and `ExtensionPopover.vue` read this. */
export const openDialogs = dialog.open;
export const openPopovers = popover.open;

export const dismissDialog = dialog.dismiss;
export const dismissPopover = popover.dismiss;

/**
 * `surfaces/openMethods.ts` reads this. It opens a frame when the user clicks
 * Open in Builder. It checks no permission, because the extension asked for nothing.
 */
export const startDialog = dialog.start;
export const startPopover = popover.start;

export const uiMethods: MethodTable = {
	// the bridge rate limits toasts. They need no permission, because they do not change the editor state
	"ui.toast": { needs: null, run: showToast },
	// a window changes nothing that a user saves, so it needs no permission
	"ui.openDialog": { needs: null, run: dialog.start },
	"ui.closeDialog": { needs: null, run: dialog.finish },
	"ui.openPopover": { needs: null, run: popover.start },
	"ui.closePopover": { needs: null, run: popover.finish },
};
