/**
 * The `.` entry of `frappe-builder-extension-sdk`. In practice, it gives only types.
 *
 * - `runtime/`: the frame half. Builder serves it to each frame as `extension-sdk.js`.
 * - `shared/`: the types, the manifest rules and the port channel. The host also imports them.
 * - `vue.ts`: the optional Vue helpers, in the bundle of the author.
 * - `../vite.js` and `../package.js`: the build plugin and the packager, which run in Node.
 *
 * No extension build reads this file. `vite.js` marks the SDK as external.
 * The import stays in the build output. The import map of the frame shell
 * then points it to the one SDK copy that Builder serves.
 *
 * On a dev server, the plugin changes the import to an absolute URL on the
 * Builder origin. That URL also gives the same SDK copy.
 *
 * This file lets the editor and the type checker of an author follow the import.
 */

export { default, type HostInfo } from "./runtime/index";
export type {
	BlockPatch,
	Control,
	ControlName,
	ContextField,
	ContextHandler,
	ContextMenuRegistration,
	ExtensionToken,
	ItemPatch,
	LeftPanelRegistration,
	NewBlock,
	PropertiesRegistration,
	SettingsRegistration,
	ShowWhen,
	SlotLoader,
	ToolbarRegistration,
} from "./runtime/methods";
export type { FrameOptions, ToastOptions, ToastType } from "./runtime/ui";
export type { SlotEntry } from "./runtime/slots";
export type { Breakpoint, Permission, EditorContext, EditorSelection, ExtensionManifest } from "./shared/types";
