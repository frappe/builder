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
export type { ContextField, ContextHandler, ItemPatch, ShowWhen, ToolbarRegistration } from "./sdk/namespaces";
export type { SlotEntry } from "./sdk/slots";
export type { Breakpoint, Permission, EditorContext, EditorSelection, ExtensionManifest } from "./types";
