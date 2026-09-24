/**
 * The `.` entry: types only, in practice.
 *
 * No extension build reads this file. `vite.js` marks `frappe-builder-extension-sdk`
 * external, so the specifier survives into the output and the frame shell's
 * import map resolves it to the one instance Builder serves. In a dev server the
 * plugin rewrites the same specifier to an absolute URL on the Builder origin,
 * which is that same instance again.
 *
 * It exists so an author's editor and type checker can follow the import.
 */

export { default, type HostInfo } from "./sdk/index";
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
} from "./sdk/namespaces";
export type { FrameOptions, ToastOptions, ToastType } from "./sdk/ui";
export type { SlotEntry } from "./sdk/slots";
export type { Breakpoint, Capability, EditorContext, EditorSelection, ExtensionManifest } from "./types";
