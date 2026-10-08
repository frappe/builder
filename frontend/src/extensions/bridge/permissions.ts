/** Checks the permission of each method that a frame calls. These functions keep no state. */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";

/** One host method. `needs` is required. A method with no permission sets `null`. */
export type HostMethod = {
	needs: Permission | null;
	/** The request handler gives the record, not the message. */
	run: (params: unknown, extension: InstalledExtension) => unknown;
};

export type MethodTable = Record<string, HostMethod>;

/**
 * The permissions that change data. Read-only mode blocks the methods that need them.
 * A new write method gets this check from its permission.
 */
const WRITE_PERMISSIONS: Permission[] = ["page.edit", "page.write", "token.write"];

export const assertWritable = (extension: InstalledExtension, method: string, needs: Permission | null) => {
	if (!needs || !WRITE_PERMISSIONS.includes(needs)) return;
	throw new ChannelCallError({
		message: `"${extension.name}" cannot run "${method}" while this page is read-only.`,
		code: "read_only",
	});
};

export const assertGranted = (extension: InstalledExtension, method: string, needs: Permission | null) => {
	if (!needs || extension.permissions.includes(needs)) return;
	throw new ChannelCallError({
		message: `"${extension.name}" was not granted ${needs}, which "${method}" needs.`,
		code: "permission_required",
	});
};
