/**
 * The `.` entry of `frappe-builder-extension-sdk`: types only, in practice.
 *
 * - `runtime/`: the frame half. Builder serves it to each frame as `extension-sdk.js`.
 * - `shared/`: the types, the manifest rules and the port channel. The host also imports them.
 * - `vue.ts`: the optional Vue helpers, in the bundle of the author.
 * - `../vite.js` and `../package.js`: the build plugin and the packager, which run in Node.
 *
 * No extension build reads this file. `vite.js` marks `frappe-builder-extension-sdk`
 * external, so the specifier survives into the output and the frame shell's
 * import map resolves it to the one instance Builder serves. In a dev server the
 * plugin rewrites the same specifier to an absolute URL on the Builder origin,
 * which is that same instance again.
 *
 * It exists so an author's editor and type checker can follow the import.
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
} from "./runtime/namespaces";
export type { FrameOptions, ToastOptions, ToastType } from "./runtime/ui";
export type { SlotEntry } from "./runtime/slots";
export type { Breakpoint, Permission, EditorContext, EditorSelection, ExtensionManifest } from "./shared/types";
