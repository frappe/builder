/**
 * What a permission means to the user who approves it.
 */

import type { Permission } from "frappe-builder-extension-sdk/types";

export const SITE_DATA_CLASS = "Site Data";

const SENSITIVE_CLASSES = [SITE_DATA_CLASS];

type PermissionDetail = {
	permissionClass: string;
	/** What it lets the extension do, in one line that a user can answer. */
	label: string;
};

export const permissionDetails: Record<Permission, PermissionDetail> = {
	"page.edit": { permissionClass: "This page", label: "Add and change blocks on this page" },
	"data.access": { permissionClass: SITE_DATA_CLASS, label: "Read and write documents on this site" },
	"method.call": { permissionClass: SITE_DATA_CLASS, label: "Run actions on your behalf" },
	"schema.write": { permissionClass: SITE_DATA_CLASS, label: "Add and remove doctypes" },
};

/** The order of the classes. The class with the widest effect is last. */
const CLASS_ORDER = ["This page", SITE_DATA_CLASS];

const CLASS_SUMMARIES: Record<string, string> = {
	"This page": "Changes to the page you are editing.",
	[SITE_DATA_CLASS]: "Records saved on your site.",
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
