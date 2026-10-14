/**
 * Each `builder.<surface>.<verb>` sends one call.
 */

export { actions, type ActionRef } from "./actions";
export { callFromEntryOnly } from "./call";
export { context, type ContextField, type ContextHandler } from "./context";
export { data, type Doc, type ListOptions } from "./data";
export {
	block,
	page,
	state,
	type BlockBindings,
	type BlockDataKey,
	type BlockPatch,
	type InsertedBlock,
	type NewBlock,
} from "./editor";
export { schema, type Doctype, type Naming, type SchemaField } from "./schema";
export {
	contextMenu,
	leftPanel,
	open,
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
