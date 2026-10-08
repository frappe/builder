/**
 * The `.` entry of `frappe-builder-extension-sdk`. It gives types to editors and type checkers.
 * The build keeps the SDK import. The frame import map points it to the SDK that Builder serves.
 */

export { default, type HostInfo } from "./runtime/index";
export type { ContextField, ContextHandler, ItemPatch, ShowWhen, ToolbarRegistration } from "./runtime/methods";
export type { SlotEntry } from "./runtime/slots";
export type { Breakpoint, Permission, EditorContext, EditorSelection, ExtensionManifest } from "./shared/types";
