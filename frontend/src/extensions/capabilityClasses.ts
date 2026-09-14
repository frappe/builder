/**
 * What a capability means to the person answering for it.
 *
 * The bridge reads a capability as a key. A user reads it as a sentence, so the
 * wording lives here and the gate keeps the key. The classes come from milestone
 * 7: a capability is grouped by how far its effect reaches, not by which method
 * it unlocks.
 *
 * Two classes reach past this editor session, so they are sensitive. A doctype
 * holds the site's own data, and a token styles every published page.
 */

import type { Capability } from "frappe-builder-extension-sdk/types";

/** The class whose answers are per doctype, so the panel lists the grants under it. */
export const SITE_DATA_CLASS = "Site data";

export const SHARED_STATE_CLASS = "Shared site state";

const SENSITIVE_CLASSES = [SITE_DATA_CLASS, SHARED_STATE_CLASS];

type CapabilityDetail = {
	capabilityClass: string;
	/** What it lets the extension do, in one line a user can answer. */
	label: string;
	/** Why allowing it reaches further than this editor session. */
	warning?: string;
};

export const capabilityDetails: Record<Capability, CapabilityDetail> = {
	"context.read": { capabilityClass: "Editor read", label: "See what you have selected" },
	"block.read": { capabilityClass: "Editor read", label: "Read a block on the canvas" },
	"page.read": { capabilityClass: "Editor read", label: "Read the whole page" },
	"block.update": { capabilityClass: "Editor write", label: "Change a block you have selected" },
	"block.insert": { capabilityClass: "Editor write", label: "Add blocks to the page" },
	"page.write": { capabilityClass: "Editor write", label: "Change the page and its client scripts" },
	"ui.dialog": { capabilityClass: "Editor chrome", label: "Open a dialog over the editor" },
	"ui.popover": { capabilityClass: "Editor chrome", label: "Open a popover beside the editor" },
	"data.access": {
		capabilityClass: SITE_DATA_CLASS,
		label: "Read and write documents on this site",
		warning: "It asks again, by doctype, and it never gets more than your own permissions.",
	},
	"token.write": {
		capabilityClass: SHARED_STATE_CLASS,
		label: "Define design tokens",
		warning: "A token it writes styles every page you already published.",
	},
	"schema.write": {
		capabilityClass: SHARED_STATE_CLASS,
		label: "Create and drop doctypes",
		warning: "Dropping a doctype drops its table and every record in it. Nothing undoes that.",
	},
};

/** The reading order of the classes, widest reach last. */
const CLASS_ORDER = ["Editor read", "Editor write", "Editor chrome", SITE_DATA_CLASS, SHARED_STATE_CLASS];

const CLASS_SUMMARIES: Record<string, string> = {
	"Editor read": "What it sees while you edit.",
	"Editor write": "What it changes on the page you have open.",
	"Editor chrome": "The windows it opens inside Builder.",
	[SITE_DATA_CLASS]: "Documents on this site, one doctype at a time.",
	[SHARED_STATE_CLASS]: "Changes that outlive this session and reach every visitor.",
};

export type CapabilityGroup = {
	name: string;
	summary: string;
	sensitive: boolean;
	capabilities: Capability[];
};

export const isSensitive = (capability: Capability) =>
	SENSITIVE_CLASSES.includes(capabilityDetails[capability]?.capabilityClass);

/**
 * The classes an extension actually asked for, each holding what it asked for.
 *
 * `keep` names a class to list even when it holds no capability. Creating a
 * doctype grants the extension that doctype outright, so an extension with
 * `schema.write` alone can hold grants the panel would otherwise have nowhere
 * to show.
 */
export const groupCapabilities = (capabilities: Capability[], keep: string[] = []): CapabilityGroup[] =>
	CLASS_ORDER.map((name) => ({
		name,
		summary: CLASS_SUMMARIES[name],
		sensitive: SENSITIVE_CLASSES.includes(name),
		capabilities: capabilities.filter(
			(capability) => capabilityDetails[capability]?.capabilityClass === name,
		),
	})).filter((group) => group.capabilities.length || keep.includes(group.name));
