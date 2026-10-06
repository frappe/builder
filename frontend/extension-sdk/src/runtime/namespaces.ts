/**
 * Each `builder.<surface>.<verb>` sends one call.
 *
 * Registrations are declarations. Write them at module scope. Each frame of
 * an extension imports the same module, so each frame reads them. So a panel
 * tab can name its document next to the tab itself. The tab and the document
 * are in different frames.
 *
 * Only the entry frame sends a declaration to the host. A panel frame keeps
 * what it needs and sends nothing. So the host gets each registration one
 * time, for any number of open frames.
 *
 * This file does not validate. The host validates each parameter. A copy of a
 * rule here would be a second rule to keep the same.
 */

import type { OpenTarget } from "../shared/types";
import { holdAction, releaseAction, type ActionHandler } from "./actions";
import { getChannel } from "./connect";
import { getActiveSlot, registerSlot } from "./slots";

/** A direct call. Any frame can make one. `update` and `run` are not declarations. */
const call = (method: string, params?: unknown) => getChannel().call(method, params);

/**
 * A declaration. The host gets it from the entry frame only.
 *
 * This function logs a refusal and also returns it. Authors usually do not
 * await a declaration at module scope. A silent refusal gives a surface that
 * does not show, with no message.
 *
 * A method that this Builder does not have shows a version gap, not an error.
 * An extension has its own release schedule. It loses only that surface. The
 * warning tells that Builder is older than the extension.
 */
export const declare = (method: string, params?: unknown) => {
	if (getActiveSlot() !== "main") return Promise.resolve();

	const sent = call(method, params);
	sent.catch((error) => {
		if ((error as { code?: string }).code === "unknown_method") {
			console.warn(`[builder] this Builder has no "${method}", so that surface is skipped`);
			return;
		}
		console.error(`[builder] "${method}" was refused`, error);
	});
	return sent;
};

/**
 * A function, or the name of an action from a different registration.
 *
 * A function cannot go through the port. The SDK keeps it in this frame and
 * sends the name of the item. A string names an action that a different call
 * registered. A frame that is not the entry frame must use a string.
 */
export type ActionRef = string | ActionHandler;

/** Keeps a handler in this frame and sends its name to the host. Entry frame only. */
const registerAction = (name: string, handler: ActionHandler) => {
	if (getActiveSlot() === "main") holdAction(name, handler);
	return declare("actions.register", { name });
};

/** Replaces a function action with its name, because a function cannot be cloned. */
const resolveAction = <T extends { name: string; action?: ActionRef }>(item: T, prefix = ""): T => {
	if (typeof item.action !== "function") return item;
	const name = `${prefix}${item.name}`;
	void registerAction(name, item.action);
	return { ...item, action: name };
};

/** The host keeps the action of a control under the section name too. So two sections can use the same control name. */
const resolveControls = (section: string, controls: Control[]) =>
	controls.map((control) => resolveAction(control, `${section}.`));

export type ShowWhen = Record<string, unknown>;

/** Gives the module that has the document of the slot. */
export type SlotLoader = () => Promise<unknown>;

export type LeftPanelRegistration = {
	name: string;
	label: string;
	icon: string;
	/** What the frame of the tab shows. It is declared here, because the tab shows it. */
	component?: SlotLoader;
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
};

export type ToolbarRegistration = {
	name: string;
	region: "left" | "center" | "right";
	icon: string;
	label?: string;
	tooltip?: string;
	/** A function, or the name of an action that this extension registered. */
	action?: ActionRef;
	badge?: string | number | null;
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
	enableWhen?: ShowWhen;
};

export type ContextMenuRegistration = {
	name: string;
	label: string;
	/** A function, or the name of an action that this extension registered. */
	action: ActionRef;
	/** The menu of the row. It is set at registration. The default is "both". */
	menu?: "canvas" | "layers" | "both";
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
	enableWhen?: ShowWhen;
};

export type SettingsRegistration = {
	name: string;
	label: string;
	title: string;
	icon: string;
	/** What the settings frame shows. It is declared here, because this item shows it. */
	component?: SlotLoader;
	before?: string;
	after?: string;
};

/** The Builder control that the host shows. A section holds values, not buttons. */
export type ControlName = "text" | "number" | "select" | "toggle" | "color" | "range";

/** One control in a property section (Tier B). The host shows it. */
export type Control = {
	name: string;
	control: ControlName;
	label?: string;
	placeholder?: string;
	/** The host writes the block itself. Needs the `page.edit` permission. */
	bind?: { attribute?: string; style?: string };
	/** The value of the extension, when no block property holds it. */
	value?: unknown;
	/** The action to run after a bound write. If the control is not bound, it runs on each change. */
	action?: ActionRef;
	/** For "select" and "toggle". A toggle option can have an icon. */
	options?: Array<{ label: string; value: string; icon?: string }>;
	min?: number;
	max?: number;
	step?: number;
	/** For each control. So one control can hide while the rest of the section stays. */
	showWhen?: ShowWhen;
};

export type PropertiesRegistration = {
	name: string;
	/** The section header. The default is `name`. */
	label?: string;
	controls: Control[];
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
};

export type ItemPatch = {
	visible?: boolean;
	enabled?: boolean;
	label?: string;
	icon?: string;
	tooltip?: string;
	badge?: string | number | null;
};

export const leftPanel = {
	register: ({ component, ...registration }: LeftPanelRegistration) => {
		// each frame records it. The panel frame uses it. No frame sends it
		if (component) registerSlot("panel", { component });
		return declare("leftPanel.register", registration);
	},
	unregister: (name: string) => call("leftPanel.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("leftPanel.update", { name, patch }),
};

/**
 * What the Open button in the details pane of the extension does.
 *
 * It is a declaration, not a slot. `kind` names a UI that the extension
 * registered in a different call. Builder opens it. With no target, the pane
 * shows no button.
 */
export const open = {
	register: (target: OpenTarget) => declare("open.register", target),
	unregister: () => call("open.unregister"),
};

export const toolbar = {
	register: (registration: ToolbarRegistration) => declare("toolbar.register", resolveAction(registration)),
	unregister: (name: string) => call("toolbar.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("toolbar.update", { name, patch }),
};

export const contextMenu = {
	register: (registration: ContextMenuRegistration) =>
		declare("contextMenu.register", resolveAction(registration)),
	unregister: (name: string) => call("contextMenu.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("contextMenu.update", { name, patch }),
};

export const properties = {
	registerSection: (registration: PropertiesRegistration) =>
		declare("properties.registerSection", {
			...registration,
			controls: resolveControls(registration.name, registration.controls),
		}),
	unregisterSection: (name: string) => call("properties.unregisterSection", { name }),
	/** Replaces the full list. Use it when the control list depends on the state of the extension. */
	setControls: (name: string, controls: Control[]) =>
		call("properties.setControls", { name, controls: resolveControls(name, controls) }),
	update: (name: string, patch: ItemPatch) => call("properties.update", { name, patch }),
};

export const settings = {
	registerItem: ({ component, ...registration }: SettingsRegistration) => {
		if (component) registerSlot("settings", { component });
		return declare("settings.registerItem", registration);
	},
	unregisterItem: (name: string) => call("settings.unregisterItem", { name }),
	update: (name: string, patch: ItemPatch) => call("settings.update", { name, patch }),
};

export type ContextField =
	"selection" | "breakpoint" | "editingMode" | "readOnly" | "isAIEnabled" | "page" | "site";

export type ContextHandler = (context: Record<string, unknown>) => void;

export const context = {
	/** The full snapshot, one time. Use it at startup. */
	get: () => call("context.get") as Promise<Record<string, unknown>>,

	/**
	 * Names the fields that this extension watches. The host sends only these
	 * fields, and only when one of them changes.
	 *
	 * Use it for a fact that no rule can state. For example, `isSVG` is in the
	 * snapshot, but it is not a rule key. Send the result back with `update`.
	 * For all other cases, use `showWhen`. It sends no messages.
	 */
	subscribe: (fields: ContextField[], handler: ContextHandler) => {
		// the host keeps one subscription for each extension. So each push has
		// all the fields that any caller named. This handler gets only its own fields
		let seen = "";
		const stop = getChannel().listen("context", (payload) => {
			const context = payload as Record<string, unknown>;
			const mine = JSON.stringify(fields.map((field) => context[field]));
			if (mine === seen) return;
			seen = mine;
			handler(context);
		});
		// a call, not a declaration. Any frame can subscribe. The host pushes to
		// each frame of the extension, so a panel gets what it asked for
		void call("context.subscribe", { fields });
		return stop;
	},
};

export type BlockPatch = {
	attributes?: Record<string, string | null>;
	/** Writes to the breakpoint that the user sees, unless `breakpoint` names a different one. */
	styles?: Record<string, string | number | null>;
	classes?: string[];
	innerHTML?: string;
	breakpoint?: "desktop" | "tablet" | "mobile";
};

export const block = {
	/** One block and its subtree, as a plain object. The id comes from the context or from a menu row. */
	get: (blockId: string) => call("block.get", { blockId }) as Promise<Record<string, unknown>>,
	/** Refused without `page.edit`. Also refused while the page is read-only. */
	update: (blockId: string, patch: BlockPatch) => call("block.update", { blockId, ...patch }),
	/**
	 * Adds a new block inside `parentId`. It goes at the end, unless `index` names a position.
	 *
	 * A block has its own `children`. So a full form or card is one call and one
	 * undo step. The host adds nothing until the full tree is valid. So a refusal
	 * does not change the page.
	 *
	 * Returns the `blockId` of the root, and `keys`. `keys` maps each `key` in the
	 * tree to its new block. The new blocks are not selected. The selection of
	 * the user does not change.
	 */
	insert: (parentId: string, block: NewBlock, index?: number) =>
		call("block.insert", { parentId, block, index }) as Promise<InsertedBlock>,
};

/** What `block.insert` adds. `element` is required. All other fields are optional. */
export type NewBlock = {
	element: string;
	attributes?: Record<string, string | null>;
	styles?: Record<string, string | number | null>;
	classes?: string[];
	innerHTML?: string;
	/** The name that the caller gives this node. The answer maps it to a `blockId`. It must be unique in one call. */
	key?: string;
	children?: NewBlock[];
};

export type InsertedBlock = {
	/** The root of the blocks that this call made. */
	blockId: string;
	/** Each `key` in the tree, and its new block. Empty when the tree has no keys. */
	keys: Record<string, string>;
};

export const page = {
	/**
	 * The tree of the canvas, as a list of roots. A node has its own `children`.
	 * Go through them to reach each block.
	 *
	 * When the user edits a component, this returns that component. `block.get`
	 * and `block.update` can find only those ids. Read `context.editingMode` to
	 * know which tree you have.
	 */
	getBlocks: () => call("page.getBlocks") as Promise<Array<Record<string, unknown>>>,

	/**
	 * Adds one script to the open page. A later call replaces the script.
	 *
	 * The script runs on the published page, never in the editor canvas. So the
	 * editor shows the settings of a block, and the page shows what it does.
	 *
	 * Each extension can have one JavaScript and one CSS script on each page.
	 * Builder asks the user before the first script of a type, and names the page.
	 * It does not ask before a replacement.
	 *
	 * Needs `page.write`. It is also refused while the page is read-only.
	 */
	attachScript: (script: PageScript) => call("page.attachScript", script) as Promise<AttachedScript>,

	/** Removes the script of that type from this extension. If there is no script, it does nothing. */
	detachScript: (type: ScriptType) => call("page.detachScript", { type }),

	/** The scripts of this extension on the open page. It does not show the scripts of others. */
	listScripts: () => call("page.listScripts") as Promise<AttachedScript[]>,
};

export type ScriptType = "JavaScript" | "CSS";

export type PageScript = {
	type: ScriptType;
	/** The full file. A later call replaces it. So send all the code that the page must run. */
	script: string;
};

export type AttachedScript = {
	name: string;
	type: ScriptType;
	script: string;
};

export const state = {
	/** All the values that this extension stored for this user. A dev extension stores them in the browser. */
	get: () => call("state.get") as Promise<Record<string, unknown>>,
	/** Merges at the top level. It never removes a key that the patch does not name. */
	set: (state: Record<string, unknown>) => call("state.set", { state }),
	unset: (key: string) => call("state.unset", { key }),
};

/** One row in `Builder Token`, as an extension gives it. */
export type ExtensionToken = {
	/** The stable id of the token in this extension. The record name is a uuid. */
	key: string;
	token_name: string;
	type: "Color" | "Dimension" | "Font";
	value: string;
	dark_value?: string;
	group?: string;
};

export const tokens = {
	/**
	 * Adds or changes rows by `key`. It never removes a row that the call does not name.
	 *
	 * It is a network call. The row must exist on the server to reach the
	 * published site. So the promise resolves only when Frappe answers.
	 */
	set: (tokens: ExtensionToken[]) => call("tokens.set", { tokens }),
	unset: (key: string) => call("tokens.unset", { key }),
};

/** One document, as Frappe keeps it. Its fields are the fields of the doctype. */
export type Doc = Record<string, unknown>;

/**
 * The options of `data.getList`. They have the same names as in
 * `createListResource`, because an extension author writes frontend code.
 */
export type ListOptions = {
	fields?: string[];
	/** A dict of equal values, or the Frappe list form: `[["status", "!=", "Open"]]`. */
	filters?: Record<string, unknown> | unknown[];
	/** These match with OR. `filters` match with AND. */
	orFilters?: Record<string, unknown> | unknown[];
	orderBy?: string;
	groupBy?: string;
	start?: number;
	/** 500 or less. The server refuses 0, because Frappe reads 0 as all rows. */
	pageLength?: number;
};

export const data = {
	/**
	 * One page of documents.
	 *
	 * Each call here needs the `data.access` permission. It runs as the user of
	 * the editor, and it reaches only the documents of that user. A refusal comes
	 * from the site. A second call does not change it.
	 */
	getList: (doctype: string, options: ListOptions = {}) =>
		call("data.getList", { doctype, ...options }) as Promise<Doc[]>,

	/** The number of documents that match. It does not get the documents. */
	getCount: (doctype: string, filters?: ListOptions["filters"]) =>
		call("data.getCount", { doctype, filters }) as Promise<number>,

	/** One full document, with its child tables. */
	getDoc: (doctype: string, name: string) => call("data.getDoc", { doctype, name }) as Promise<Doc>,

	/** Adds a new document. Returns the new document. */
	insert: (doctype: string, doc: Doc) => call("data.insert", { doctype, doc }) as Promise<Doc>,

	/** Changes only the fields that `doc` names. Returns the saved document. */
	update: (doctype: string, name: string, doc: Doc) =>
		call("data.update", { doctype, name, doc }) as Promise<Doc>,

	delete: (doctype: string, name: string) => call("data.delete", { doctype, name }),
};

/** One field of a doctype that an extension makes. */
export type SchemaField = {
	fieldname?: string;
	label?: string;
	/** A layout break and a Heading need no fieldname. A Table needs a child doctype, so it is not allowed. */
	fieldtype: string;
	/** The linked doctype for a Link. For a Select, the choices, one on each line. */
	options?: string;
	reqd?: boolean;
	unique?: boolean;
	default?: unknown;
	in_list_view?: boolean;
	read_only?: boolean;
	description?: string;
};

export type Doctype = {
	doctype: string;
	istable: boolean;
	fields: SchemaField[];
};

/** How a new document gets its name. It is set at creation. A later change renames nothing. */
export type Naming = "hash" | "autoincrement" | "prompt";

export const schema = {
	/**
	 * Makes a new custom doctype. This extension owns it.
	 *
	 * Builder first asks the user, with the name. If the user says no, the call
	 * fails with the code `refused`. It needs the `schema.write` permission. The
	 * **user** must also be a System Manager. Frappe needs create permission on
	 * `DocType`, and nothing here changes that.
	 */
	createDoctype: (
		doctype: string,
		fields: SchemaField[],
		options: { naming?: Naming; istable?: boolean } = {},
	) => call("schema.createDoctype", { doctype, fields, ...options }) as Promise<Doctype>,

	/** The field list of a doctype that the user can read. */
	getDoctype: (doctype: string) => call("schema.getDoctype", { doctype }) as Promise<Doctype>,

	/**
	 * Adds fields, and changes the existing fields by fieldname.
	 *
	 * It never removes a field that the call does not name. A removed field
	 * removes a column and its data. Only the extension that made the doctype
	 * can call this.
	 */
	updateDoctype: (doctype: string, fields: SchemaField[]) =>
		call("schema.updateDoctype", { doctype, fields }) as Promise<Doctype>,

	/** Removes a doctype that this extension made, and its table. Builder asks the user first. */
	deleteDoctype: (doctype: string) => call("schema.deleteDoctype", { doctype }),

	/** Each doctype that this extension made, and if it still exists. */
	listDoctypes: () => call("schema.listDoctypes") as Promise<Array<{ doctype: string; exists: boolean }>>,
};

export const actions = {
	/**
	 * The handler stays in this frame. The host gets only the name.
	 *
	 * Only the entry frame keeps and names the handler. So the host always
	 * calls the frame that lives longest.
	 */
	register: (name: string, handler: ActionHandler) => registerAction(name, handler),
	unregister: (name: string) => {
		if (getActiveSlot() !== "main") return Promise.resolve();
		releaseAction(name);
		return call("actions.unregister", { name });
	},
	/** Runs an action of this extension from any of its frames. */
	run: (name: string, context?: Record<string, unknown>) => call("actions.run", { name, context }),
};
