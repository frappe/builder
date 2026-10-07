/**
 * What a permission means to the user who approves it.
 *
 * The bridge reads a permission as a key. A user reads it as a sentence. So
 * the words are here, and the gate keeps the key. Each class groups
 * permissions by how far their effect goes, not by the methods they allow.
 *
 * Two classes go past this editor session, so they are sensitive. A doctype
 * has the data of the site, and a token styles each published page.
 */

import type { Permission } from "frappe-builder-extension-sdk/types";

export const SITE_DATA_CLASS = "Site data";

export const SHARED_STATE_CLASS = "Shared site state";

const SENSITIVE_CLASSES = [SITE_DATA_CLASS, SHARED_STATE_CLASS];

type PermissionDetail = {
	permissionClass: string;
	/** What it lets the extension do, in one line that a user can answer. */
	label: string;
	/** Why its effect goes past this editor session. */
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

/** The order of the classes. The class with the widest effect is last. */
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

/** The classes that an extension asked for. Each class has the permissions that it asked for. */
export const groupPermissions = (permissions: Permission[]): PermissionGroup[] =>
	CLASS_ORDER.map((name) => ({
		name,
		summary: CLASS_SUMMARIES[name],
		sensitive: SENSITIVE_CLASSES.includes(name),
		permissions: permissions.filter((permission) => permissionDetails[permission]?.permissionClass === name),
	})).filter((group) => group.permissions.length);
