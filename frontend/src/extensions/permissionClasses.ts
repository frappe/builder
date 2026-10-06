/**
 * What a permission means to the person answering for it.
 *
 * The bridge reads a permission as a key. A user reads it as a sentence, so the
 * wording lives here and the gate keeps the key. The classes come from milestone
 * 7: a permission is grouped by how far its effect reaches, not by which method
 * it unlocks.
 *
 * Two classes reach past this editor session, so they are sensitive. A doctype
 * holds the site's own data, and a token styles every published page.
 */

import type { Permission } from "frappe-builder-extension-sdk/types";

export const SITE_DATA_CLASS = "Site data";

export const SHARED_STATE_CLASS = "Shared site state";

const SENSITIVE_CLASSES = [SITE_DATA_CLASS, SHARED_STATE_CLASS];

type PermissionDetail = {
	permissionClass: string;
	/** What it lets the extension do, in one line a user can answer. */
	label: string;
	/** Why allowing it reaches further than this editor session. */
	warning?: string;
};

export const permissionDetails: Record<Permission, PermissionDetail> = {
	"page.edit": { permissionClass: "Editor write", label: "Change and add blocks on the page" },
	"page.write": { permissionClass: "Editor write", label: "Add client scripts to the page" },
	"data.access": {
		permissionClass: SITE_DATA_CLASS,
		label: "Read and write documents on this site",
		warning: "It never gets more than the permissions of the person using it.",
	},
	"token.write": {
		permissionClass: SHARED_STATE_CLASS,
		label: "Define design tokens",
		warning: "A token it writes styles every page you already published.",
	},
	"method.call": {
		permissionClass: SITE_DATA_CLASS,
		label: "Run actions from installed apps",
		warning: "It never gets more than the permissions of the person using it.",
	},
	"schema.write": {
		permissionClass: SHARED_STATE_CLASS,
		label: "Create and drop doctypes",
		warning: "Dropping a doctype drops its table and every record in it. Nothing undoes that.",
	},
};

/** The reading order of the classes, widest reach last. */
const CLASS_ORDER = ["Editor write", SITE_DATA_CLASS, SHARED_STATE_CLASS];

const CLASS_SUMMARIES: Record<string, string> = {
	"Editor write": "What it changes on the page you have open.",
	[SITE_DATA_CLASS]: "Documents on this site, within each user's own permissions.",
	[SHARED_STATE_CLASS]: "Changes that outlive this session and reach every visitor.",
};

export type PermissionGroup = {
	name: string;
	summary: string;
	sensitive: boolean;
	permissions: Permission[];
};

export const isSensitive = (permission: Permission) =>
	SENSITIVE_CLASSES.includes(permissionDetails[permission]?.permissionClass);

/** The classes an extension actually asked for, each holding what it asked for. */
export const groupPermissions = (permissions: Permission[]): PermissionGroup[] =>
	CLASS_ORDER.map((name) => ({
		name,
		summary: CLASS_SUMMARIES[name],
		sensitive: SENSITIVE_CLASSES.includes(name),
		permissions: permissions.filter((permission) => permissionDetails[permission]?.permissionClass === name),
	})).filter((group) => group.permissions.length);
