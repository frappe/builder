/**
 * The `.` entry. In practice, it gives only types.
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

export { default, type HostInfo } from "./sdk/index";
export type { ContextField, ContextHandler, ItemPatch, ShowWhen, ToolbarRegistration } from "./sdk/namespaces";
export type { SlotEntry } from "./sdk/slots";
export type { Breakpoint, Permission, EditorContext, EditorSelection, ExtensionManifest } from "./types";
