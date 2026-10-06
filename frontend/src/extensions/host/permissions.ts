/**
 * The gate in front of every method a frame calls.
 *
 * Pure: the bridge holds the record and passes it in, so nothing here reads a
 * resource or keeps state. The permission keys live in `../types`, beside the
 * spelling the SDK reads.
 */

import { ChannelCallError } from "frappe-builder-extension-sdk/transport";
import type { Permission, InstalledExtension } from "frappe-builder-extension-sdk/types";

/**
 * One method the host answers.
 *
 * `needs` is required rather than optional, so a method that needs no grant says
 * so out loud. A method cannot reach the table with its gate forgotten.
 */
export type HostMethod = {
	needs: Permission | null;
	/** The record comes from the dispatcher's closure, never from the wire. */
	run: (params: unknown, extension: InstalledExtension) => unknown;
};

export type MethodTable = Record<string, HostMethod>;

/**
 * The permissions that change something a user can see and save.
 *
 * Read-only mode is enforced once, in the bridge, rather than trusted to each
 * write method. Naming the permissions rather than the methods means a
 * write method added later is covered before it is written.
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
