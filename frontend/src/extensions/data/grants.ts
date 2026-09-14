/**
 * Which doctypes an extension may touch, and how it asks.
 *
 * The capability `data.access` says an extension works with site data at all,
 * and an admin answers that at install. A grant says which doctype, and the
 * **user** answers that here, while the editor runs. Frappe's own permission
 * decides whether this user may do it, and no call in this tree widens it.
 *
 * A grant is asked for, never assumed. `data.requestAccess` is the one method
 * that opens a dialog. Every other data method refuses without a grant, so no
 * modal lands while the user drags a block, and a loop of calls cannot stack a
 * pile of dialogs. `data.getAccess` lets an extension check first and draw its
 * own "connect to Contacts" button.
 *
 * Nothing is cached. The record is the only owner of the answer (rule 22), and a
 * stale copy here would cost the user a second dialog for a grant they already
 * gave.
 */

import { createResource } from "frappe-ui";
import { ref } from "vue";
import { bridge } from "../host/bridge";
import type { MethodTable } from "../host/capabilities";
import { fields, refuse, text } from "../params";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";

export const ACCESS = ["read", "write", "delete"] as const;
export type Access = (typeof ACCESS)[number];

export const ACCESS_ANSWERS = ["allowed", "denied", "not asked"] as const;
export type AccessAnswer = (typeof ACCESS_ANSWERS)[number];

/**
 * What the server says about one extension and one doctype: one answer for each
 * access. A denied access is not asked about again until the user changes it in
 * the Extensions panel.
 */
export type Grant = { doctype: string } & Record<Access, AccessAnswer>;

/**
 * Doctypes the prompt warns about twice.
 *
 * None of these is blocked. A user who means it can still allow one, and every
 * write is still bounded by that user's own permission. The list exists because
 * "allow Acme to write Contact" and "allow Acme to write User" should not read
 * the same way.
 *
 * `Builder User Extension` is the sharpest case: write access to it lets an
 * extension rewrite its own capability list, so the install-time gate becomes
 * advisory.
 */
export const SENSITIVE_DOCTYPES = new Set([
	"Builder User Extension",
	"Builder Extension Grant",
	"Builder Extension State",
	"Builder Token",
	"User",
	"Role",
	"Role Profile",
	"User Permission",
	"DocShare",
	"DocType",
	"Custom Field",
	"Property Setter",
	"Server Script",
	"Client Script",
	"Builder Client Script",
	// each of these carries code or a template the site later runs. `Web Form` is
	// the sharpest: frappe puts no gate on its `client_script` (`web_form.py:90`),
	// so write access to it is arbitrary JavaScript on a public page, at the
	// site's own origin, for anonymous visitors
	"Web Form",
	"Print Format",
	"Notification",
	"Webhook",
	"System Settings",
	"Website Settings",
	"Builder Settings",
	"Social Login Key",
	"Email Account",
]);

/** One-shot, the way `tokenMethods.ts:27` calls a whitelisted method. */
const invoke = (url: string, params: Record<string, unknown>) => createResource({ url }).submit(params);

/**
 * Which question the dialog asks.
 *
 * `access` is the doctype grant, and its answer becomes a record. The other two
 * ask about one act — creating or dropping a doctype, putting a script on a
 * page — and record nothing, because there is no standing permission to
 * remember: the next act asks again.
 */
export type PromptKind = "access" | "schema" | "script";

export type GrantPrompt = {
	kind: PromptKind;
	extension: InstalledExtension;
	/** The doctype an access or schema prompt names. The page route a script prompt names. */
	subject: string;
	/** What is still not asked. An access the user already allowed or denied is not asked about again. */
	access: Access[];
	sensitive: boolean;
	/** For a schema prompt: the verb, in the words the dialog uses. */
	act?: "create" | "delete";
};

/** Read by `ExtensionGrantDialog.vue`. One prompt stands at a time, so this is a single ref. */
export const pendingPrompt = ref<GrantPrompt | null>(null);

let answer: ((granted: boolean) => void) | null = null;

/**
 * The user's answer, from the dialog. Dismissing it counts as no, which is what
 * every browser permission prompt does and the only honest reading of a
 * question nobody answered.
 */
export const answerPrompt = (granted: boolean) => {
	const settle = answer;
	answer = null;
	pendingPrompt.value = null;
	settle?.(granted);
};

/** Which extensions already have a teardown hook, so asking twice adds one hook. */
const hooked = new Set<string>();

const hookTeardown = (extension: InstalledExtension) => {
	if (hooked.has(extension.name)) return;
	hooked.add(extension.name);
	bridge.registerTeardown(extension.name, () => {
		hooked.delete(extension.name);
		// a prompt outliving the extension that asked would ask on behalf of nobody
		if (pendingPrompt.value?.extension.name === extension.name) answerPrompt(false);
	});
};

/**
 * One dialog at a time, in the order the requests arrived.
 *
 * Two frames of one extension can ask at once, and so can two extensions. A
 * queue is what stops the second request drawing over the first, and it costs a
 * wait rather than a refusal.
 */
let queue: Promise<unknown> = Promise.resolve();

const enqueue = <T>(task: () => Promise<T>): Promise<T> => {
	const next = queue.then(task, task);
	queue = next.catch(() => undefined);
	return next;
};

const readDoctype = (params: unknown) => text(fields(params).doctype, "doctype");

const readAccess = (value: unknown): Access[] => {
	if (!Array.isArray(value) || !value.length) {
		// escaped rather than single-quoted, the way tokenMethods.ts:58 writes the
		// same refusal: eslint wants double quotes and prettier wants fewer escapes
		throw refuse('"access" must be a non-empty list.', "invalid_params");
	}
	const unknown = value.filter((entry) => !ACCESS.includes(entry as Access));
	if (unknown.length) {
		throw refuse(`"access" must hold only: ${ACCESS.join(", ")}.`, "invalid_params");
	}
	return value as Access[];
};

/**
 * A fresh plain object, never what the resource resolved with.
 *
 * `createResource` keeps its `data` reactive, so it answers with a Vue proxy,
 * and `postMessage` cannot clone a proxy — the same fault `uiMethods.ts` hit
 * with dialog props. Rebuilding the shape here fixes it and checks what the
 * server sent in the same step.
 */
const readAnswer = (value: unknown): AccessAnswer =>
	ACCESS_ANSWERS.includes(value as AccessAnswer) ? (value as AccessAnswer) : "not asked";

const toGrant = (value: unknown, doctype: string): Grant => {
	const sent = fields(value);
	return {
		doctype,
		read: readAnswer(sent.read),
		write: readAnswer(sent.write),
		delete: readAnswer(sent.delete),
	};
};

const readGrant = (extension: InstalledExtension, doctype: string) =>
	invoke("builder.extensions.data.get_extension_grant", {
		extension: extension.name,
		doctype,
	}).then((sent: unknown) => toGrant(sent, doctype));

const ask = (request: GrantPrompt) =>
	new Promise<boolean>((resolve) => {
		answer = resolve;
		pendingPrompt.value = request;
	});

/**
 * Asks the user to allow one act on the schema, and remembers nothing.
 *
 * Creating a table and dropping one are the two most consequential things this
 * API can do, and Frappe's own gate — create permission on `DocType` — only
 * says the user *could* do it by hand, not that they meant this extension to.
 * So the act is named, once, each time.
 *
 * Exported for `schemaMethods.ts`, which is the only caller.
 */
export const confirmSchema = (extension: InstalledExtension, doctype: string, act: "create" | "delete") => {
	hookTeardown(extension);
	return enqueue(() =>
		ask({ kind: "schema", extension, subject: doctype, act, access: [], sensitive: act === "delete" }),
	);
};

/**
 * Asks the user to let this extension put a script on one page, and remembers
 * nothing.
 *
 * A client script is JavaScript on a public page at the site's own origin, and
 * nothing bounds it once it lands. Frappe's own gate — write permission on
 * `Builder Client Script` — says the user could add one by hand, not that they
 * meant this extension to. So the page is named, once, each time a script is
 * created. Rewriting a script the extension already owns asks again for
 * nothing: the user allowed this extension to run code on this page, and it is
 * the same code's next version.
 *
 * Exported for `pageMethods.ts`, which is the only caller.
 */
export const confirmPageScript = (extension: InstalledExtension, route: string) => {
	hookTeardown(extension);
	return enqueue(() => ask({ kind: "script", extension, subject: route, access: [], sensitive: true }));
};

const prompt = async (extension: InstalledExtension, doctype: string, access: Access[]) => {
	hookTeardown(extension);
	const granted = await ask({
		kind: "access",
		extension,
		subject: doctype,
		access,
		sensitive: SENSITIVE_DOCTYPES.has(doctype),
	});

	return invoke("builder.extensions.data.record_extension_grant", {
		extension: extension.name,
		doctype,
		access,
		denied: !granted,
	}).then((sent: unknown) => toGrant(sent, doctype));
};

/**
 * Asks the user about each access nobody answered yet.
 *
 * An access the user allowed or denied is not asked about again. When every
 * access named is answered, this returns the grant without a dialog. When
 * another extension is mid-prompt, this one waits its turn.
 */
const requestAccess = async (params: unknown, extension: InstalledExtension) => {
	const sent = fields(params);
	const doctype = readDoctype(sent);
	const access = readAccess(sent.access);

	const current = await readGrant(extension, doctype);
	const unasked = access.filter((entry) => current[entry] === "not asked");
	if (!unasked.length) return current;

	return enqueue(() => prompt(extension, doctype, unasked));
};

const getAccess = (params: unknown, extension: InstalledExtension) =>
	readGrant(extension, readDoctype(params));

export const grantMethods: MethodTable = {
	// not a page write, so the read-only refusal does not reach it: read-only is
	// about the page being edited, and a Contact is not that page
	"data.requestAccess": { needs: "data.access", run: requestAccess },
	"data.getAccess": { needs: "data.access", run: getAccess },
};
