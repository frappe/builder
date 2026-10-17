/**
 * The gate for each method that a frame calls.
 */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";

/**
 * One method that the host answers.
 *
 * `needs` is required. So a method with no permission must say `null`.
 * No method can go into the table without a gate.
 */
export type HostMethod = {
	needs: Permission | null;
	/** The record comes from the request handler. It never comes from the message. */
	run: (params: unknown, extension: InstalledExtension) => unknown;
};

export type MethodTable = Record<string, HostMethod>;

/**
 * The permissions that change data that a user can see and save.
 *
 * The bridge applies read-only mode in one place. Each write method does not
 * check it. This list names permissions, not methods. So a new write method
 * gets the check automatically.
 */
const WRITE_PERMISSIONS: Permission[] = ["page.edit"];

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

/** The check for a `bind` control at registration. At that time, there is no call to gate. */
export const canEdit = (extension: InstalledExtension) => extension.permissions.includes("page.edit");
