/**
 * The page itself: the tree an extension reads, and the scripts it puts there.
 *
 * A client script is the one thing an extension writes that outlives the editor
 * and runs for a visitor. `builder/extension_page.py` carries the reasoning and
 * the ownership rules. This file holds the two the server cannot: the page is
 * the open one, and a create asks the user first.
 *
 * The snapshot deliberately leaves the tree out: it is large and it
 * changes on every keystroke, so an extension asks for it rather than being sent
 * it. `block.get` serves the extension that needs one node.
 *
 * The tree comes from the canvas, not from `pageStore.pageBlocks`, for two
 * reasons. Undo replaces the root instance, so `pageBlocks` goes stale after the
 * first undo. And `block.get` and `block.update` both resolve against the
 * canvas, so reading a different tree would hand back ids the other two methods
 * could not resolve.
 *
 * While the user edits a component, the canvas holds that fragment rather than
 * the page, and this answers with the fragment. The alternative returns ids an
 * extension cannot act on. `context.editingMode` says which it is looking at.
 */

import usePageStore from "@/stores/pageStore";
import useCanvasStore from "@/stores/canvasStore";
import { getBlockObject } from "@/utils/helpers";
import { createResource } from "frappe-ui";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { confirmPageScript } from "../data/grants";
import type { MethodTable } from "../host/capabilities";
import { fields, oneOf, refuse, text } from "../params";

/**
 * A list, because that is the shape Builder stores a page in, even though the
 * list always holds one root today.
 *
 * No canvas is a refusal rather than an empty list, so an extension that called
 * before the editor was ready can tell that apart from a page with nothing on
 * it.
 */
const getBlocks = () => {
	const root = useCanvasStore().activeCanvas?.getRootBlock();
	if (!root) throw refuse("No canvas is open.", "no_canvas");
	return [getBlockObject(root)];
};

const SCRIPT_TYPES = ["JavaScript", "CSS"] as const;

/** Rebuilt plain, because `createResource` answers with its reactive `data`. */
const plain = <T>(value: T): T => JSON.parse(JSON.stringify(value ?? null));

const invoke = (method: string, params: Record<string, unknown>) =>
	createResource({ url: `builder.extensions.page.${method}` })
		.submit(params)
		.then(plain)
		.catch((thrown: unknown) => {
			const sent = thrown as { messages?: string[]; message?: string };
			throw refuse(sent.messages?.[0] || sent.message || "The server refused that call.", "server_error");
		});

/**
 * The page a script lands on is always the open one.
 *
 * An extension naming a page would be able to write code onto a page nobody is
 * looking at, and the confirmation would name a route the user is not on.
 */
const openPage = () => {
	const page = usePageStore().activePage;
	if (!page) throw refuse("No page is open.", "no_page");
	return page;
};

const readScriptType = (params: unknown) => oneOf(fields(params).type, SCRIPT_TYPES, "type");

/**
 * Creates this extension's script of that type on the open page, or rewrites the
 * one already there.
 *
 * Only a create asks the user. The confirmation is about running this
 * extension's code on this page at all, and that answer does not become stale
 * when the extension ships its next version of the same script.
 */
const attachScript = async (params: unknown, extension: InstalledExtension) => {
	const type = readScriptType(params);
	const script = text(fields(params).script, "script");
	const page = openPage();

	const mine = await invoke("list_scripts", { extension: extension.name, page: page.name });
	const exists = (mine as Array<{ type: string }>).some((row) => row.type === type);

	if (!exists && !(await confirmPageScript(extension, page.route || page.name))) {
		throw refuse(`The user did not allow "${extension.name}" to run a script on this page.`, "refused");
	}

	return invoke("attach_script", {
		extension: extension.name,
		page: page.name,
		script_type: type,
		script,
	});
};

const detachScript = (params: unknown, extension: InstalledExtension) =>
	invoke("detach_script", {
		extension: extension.name,
		page: openPage().name,
		script_type: readScriptType(params),
	});

const listScripts = (_params: unknown, extension: InstalledExtension) =>
	invoke("list_scripts", { extension: extension.name, page: openPage().name });

export const pageMethods: MethodTable = {
	"page.getBlocks": { needs: "page.read", run: getBlocks },
	"page.attachScript": { needs: "page.write", run: attachScript },
	"page.detachScript": { needs: "page.write", run: detachScript },
	// its own scripts, so the capability that wrote them is the one that reads them
	"page.listScripts": { needs: "page.write", run: listScripts },
};
