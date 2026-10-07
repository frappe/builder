/**
 * The words that the host and the SDK both use.
 *
 * Domain types come first. Then come the shapes that go through a port.
 * `transport/messages.ts` has the checks for these shapes.
 */

import { PERMISSIONS, PROTOCOL_VERSION } from "./manifest.js";

/** The five documents that an extension can have. The host names one in the handshake. */
export type ExtensionSlot = "main" | "panel" | "dialog" | "popover" | "settings";

/**
 * What Builder opens when the user opens this extension from its details pane.
 *
 * If an extension declares no target, Builder shows no Open button.
 * Builder shows the popover or the dialog in its own frame. The user
 * pressed a button in Builder, and the extension asked for nothing.
 */
export type OpenTarget =
	| { kind: "popover"; width?: number; height?: number }
	| { kind: "dialog"; title?: string }
	| { kind: "leftPanel"; name: string };

/** Each permission that the bridge uses to gate a method. The server has the same list. */
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

/** One extension that this user runs, as the editor mounts it. */
export type InstalledExtension = {
	name: string; // "acme/icons"
	label: string;
	/** A short summary for the Extensions panel. */
	description?: string;
	permissions: Permission[];
	/** A data URI for the SVG in the package. Not set if the package has no SVG. */
	icon?: string;
	/**
	 * The URL of the entry module. Builder serves an installed extension, with the
	 * checksum of the build in the URL. A dev server serves a development extension.
	 */
	entryUrl: string;
};

export type Breakpoint = "desktop" | "tablet" | "mobile";

/**
 * The data that the host gives about the selection.
 *
 * `count` and `blockIds` describe the full selection. Each other field
 * describes one block. So a field has a value only when one block is
 * selected. With three blocks selected, `isText: true` would be false.
 *
 * So a rule that names one of these fields does not match when the user
 * selects more than one block. The matcher compares strictly, and no value
 * equals `undefined`. The item then hides. It does not act on the wrong block.
 *
 * The context menu is not an exception. A right-click names one block. The
 * host fills these fields from that block, whatever else is selected.
 *
 * The kind checks are separate booleans, not one `blockType`. `Block` keeps
 * them independent. For example, a block can be a link and a container.
 */
export type EditorSelection = {
	count: number;
	/** Each selected block, in canvas order. Always present. */
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

/** A snapshot of one block. It says nothing about the full selection. */
export type BlockSnapshot = Omit<EditorSelection, "count" | "blockIds">;

/**
 * The snapshot that an extension reads. It is not the live state of Builder.
 *
 * Add a field only when a built-in `condition` already reads it.
 * It is easy to add a field later. It is difficult to remove one.
 */
export type EditorContext = {
	selection: EditorSelection;
	breakpoint: Breakpoint;
	editingMode: "page" | "fragment";
	readOnly: boolean;
	isAIEnabled: boolean;
	/** Null when no page is open. So no code reads an empty route as a real route. */
	page: { route: string; isTemplate: boolean; isStandard: boolean; published: boolean } | null;
	site: { isDeveloperMode: boolean; isFCSite: boolean };
};

/**
 * An extension has its own release schedule. It can run on an older Builder.
 * So each message names the version that it uses.
 */
/**
 * The initial and only message on the window. The port is sent via this message.
 * All other messages use the port.
 *
 * It names no extension and no permission. The host knows the extension of
 * each port. Only the host applies permissions.
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
	/** Set when the caller must act on the reason, for example "unsupported_version". */
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

/** Both sides send all three types. So no shape has a direction. */
export type PortMessage = RequestMessage | ResponseMessage | EventMessage;

/**
 * A message with a known shape and a version that this Builder can not know.
 * The channel answers this message. It does not ignore it. So an extension
 * for a newer Builder learns why its call failed.
 */
export type AnyVersionMessage = (
	Omit<RequestMessage, "v"> | Omit<ResponseMessage, "v"> | Omit<EventMessage, "v">
) & {
	v: number;
};
