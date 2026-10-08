/** The types that the host and the SDK share. `transport/messages.ts` checks the message shapes. */

import { PERMISSIONS, PROTOCOL_VERSION } from "./manifest.js";

/** The five documents that an extension can have. The host names one in the handshake. */
export type ExtensionSlot = "main" | "panel" | "dialog" | "popover" | "settings";

/** The permissions that the bridge checks. The server has the same list. */
export { PERMISSIONS, PROTOCOL_VERSION };

export type Permission = (typeof PERMISSIONS)[number];

export type ExtensionManifest = {
	v: typeof PROTOCOL_VERSION;
	name: string;
	label: string;
	description: string;
	version: string;
	entry: "main.js";
	icon?: string;
	permissions: Permission[];
};

/** One extension that the editor mounts. */
export type InstalledExtension = {
	name: string; // "acme/icons"
	label: string;
	/** A short summary for the Extensions panel. */
	description?: string;
	permissions: Permission[];
	/** A data URI for the icon. Empty if the package has no icon. */
	icon?: string;
	/** The URL of the entry module. It is on Builder with the build checksum, or on a dev server. */
	entryUrl: string;
};

export type Breakpoint = "desktop" | "tablet" | "mobile";

/**
 * The selection. `count` and `blockIds` are for all selected blocks.
 * The other fields have a value only for one block. So a rule with them hides the item for many blocks.
 */
export type EditorSelection = {
	count: number;
	/** The selected blocks, in canvas order. */
	blockIds: string[];
	blockId?: string;
	element?: string; // the tag. All the kind checks come from it
	isRoot?: boolean;
	isText?: boolean;
	isImage?: boolean;
	isHTML?: boolean;
	isSVG?: boolean;
	isLink?: boolean;
	isContainer?: boolean;
	isVideo?: boolean;
	isInput?: boolean;
	isRepeater?: boolean;
	isComponent?: boolean; // isExtendedFromComponent
	isChildOfComponent?: boolean;
};

/** A snapshot of one block. */
export type BlockSnapshot = Omit<EditorSelection, "count" | "blockIds">;

/**
 * The snapshot that an extension reads. It is not the live state of Builder.
 * Add a field only when a built-in `condition` reads it. It is difficult to remove a field.
 */
export type EditorContext = {
	selection: EditorSelection;
	breakpoint: Breakpoint;
	editingMode: "page" | "fragment";
	readOnly: boolean;
	isAIEnabled: boolean;
	/** Null when no page is open. */
	page: { route: string; isTemplate: boolean; isStandard: boolean; published: boolean } | null;
	site: { isDeveloperMode: boolean; isFCSite: boolean };
};

/**
 * The only message on the window. It sends the port. All other messages use the port.
 * Each message has a version, because an extension can run on an older Builder.
 */
export type ConnectMessage = {
	v: typeof PROTOCOL_VERSION;
	type: "connect";
	slot: ExtensionSlot;
	/** The URL of the entry module that this frame imports. */
	entryUrl: string;
	theme: "light" | "dark";
	props?: Record<string, unknown>; // set only for a dialog
};

export type ChannelError = {
	message: string;
	/** A code that the caller can act on, for example "unsupported_version". */
	code?: string;
};

export type RequestMessage = {
	v: typeof PROTOCOL_VERSION;
	type: "request";
	id: number;
	method: string;
	params?: unknown;
};

export type ResponseMessage = {
	v: typeof PROTOCOL_VERSION;
	type: "response";
	id: number;
	result?: unknown;
	error?: ChannelError;
};

export type EventMessage = {
	v: typeof PROTOCOL_VERSION;
	type: "event";
	event: string;
	payload?: unknown;
};

/** Both sides send all three types. */
export type PortMessage = RequestMessage | ResponseMessage | EventMessage;

/** A message with a version that this Builder does not know. The channel answers it with an error. */
export type AnyVersionMessage = (
	Omit<RequestMessage, "v"> | Omit<ResponseMessage, "v"> | Omit<EventMessage, "v">
) & {
	v: number;
};
