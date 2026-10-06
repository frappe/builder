/**
 * The gate for each method that a frame calls.
 *
 * The functions here are pure. The bridge keeps the record and gives it to
 * them. So no code here reads a resource or keeps state. The permission keys
 * are in the SDK types, with the names that the SDK reads.
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
	/** The record comes from the dispatcher. It never comes from the message. */
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
