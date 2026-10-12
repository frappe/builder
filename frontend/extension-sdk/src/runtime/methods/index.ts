/**
 * Each `builder.<surface>.<verb>` sends one call.
 *
 * Write registrations at module scope. Each frame of an extension imports the
 * same module, so each frame reads them. So a panel tab can name its document
 * next to the tab itself. The tab and the document are in different frames.
 *
 * Only the entry frame sends a registration to the host. A panel frame keeps
 * what it needs and sends nothing. So the host gets each registration one
 * time, for any number of open frames.
 *
 * This file does not validate. The host validates each parameter. A copy of a
 * rule here would be a second rule to keep the same.
 */

export { actions, type ActionRef } from "./actions";
export { callFromEntryOnly } from "./call";
export { context, type ContextField, type ContextHandler } from "./context";
export { data, type Doc, type ListOptions } from "./data";
export { block, page, state, type BlockPatch, type InsertedBlock, type NewBlock } from "./editor";
export {
	contextMenu,
	leftPanel,
	properties,
	settings,
	toolbar,
	type ContextMenuRegistration,
	type Control,
	type ControlName,
	type ItemPatch,
	type LeftPanelRegistration,
	type PropertiesRegistration,
	type SettingsRegistration,
	type ShowWhen,
	type SlotLoader,
	type ToolbarRegistration,
} from "./surfaces";
