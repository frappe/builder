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

import { setHandler, deleteHandler, type ActionHandler } from "./actions";
import { getChannel } from "./connect";
import { getActiveSlot } from "./slots";

/** A direct call. Any frame can make one. `update` and `run` are not registrations. */
const call = (method: string, params?: unknown) => getChannel().call(method, params);

/**
 * A call that only the entry frame sends. In other frames it does nothing.
 * Use it for registrations at module scope. Every frame runs that code, and
 * the host still gets each registration one time.
 *
 * This function logs a refusal and also returns it. Authors usually do not
 * await a registration at module scope. A silent refusal gives a surface that
 * does not show, with no message.
 *
 * A method that this Builder does not have shows a version gap, not an error.
 * An extension has its own release schedule. It loses only that surface. The
 * warning tells that Builder is older than the extension.
 */
export const callFromEntryOnly = (method: string, params?: unknown) => {
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
	if (getActiveSlot() === "main") setHandler(name, handler);
	return callFromEntryOnly("actions.register", { name });
};

/** Replaces a function action with its name, because a function cannot be cloned. */
const resolveAction = <T extends { name: string; action?: ActionRef }>(item: T): T => {
	if (typeof item.action !== "function") return item;
	void registerAction(item.name, item.action);
	return { ...item, action: item.name };
};

export type ShowWhen = Record<string, unknown>;

export type ToolbarRegistration = {
	name: string;
	region: "left" | "center" | "right";
	icon: string;
	label?: string;
	tooltip?: string;
	/** A function, or the name of an action that this extension registered. */
	action?: ActionRef;
	badge?: string | number | null;
	/** In the right region, these place a button among the extension buttons only. Builder's own buttons stay at the right end. */
	before?: string;
	after?: string;
	showWhen?: ShowWhen;
	enableWhen?: ShowWhen;
};

export type ItemPatch = {
	visible?: boolean;
	enabled?: boolean;
	label?: string;
	icon?: string;
	tooltip?: string;
	badge?: string | number | null;
};

export const toolbar = {
	register: (registration: ToolbarRegistration) =>
		callFromEntryOnly("toolbar.register", resolveAction(registration)),
	unregister: (name: string) => call("toolbar.unregister", { name }),
	update: (name: string, patch: ItemPatch) => call("toolbar.update", { name, patch }),
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
		// a call, not a registration. Any frame can subscribe. The host pushes to
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
};

export const state = {
	/** All the values that this extension stored for this user. A dev extension stores them in the browser. */
	get: () => call("state.get") as Promise<Record<string, unknown>>,
	/** Merges at the top level. It never removes a key that the patch does not name. */
	set: (state: Record<string, unknown>) => call("state.set", { state }),
	unset: (key: string) => call("state.unset", { key }),
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
	 *
	 * Design tokens and client scripts are documents too. Use the `Builder Token`
	 * and `Builder Client Script` doctypes.
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
		deleteHandler(name);
		return call("actions.unregister", { name });
	},
	/** Runs an action of this extension from any of its frames. */
	run: (name: string, context?: Record<string, unknown>) => call("actions.run", { name, context }),
};
