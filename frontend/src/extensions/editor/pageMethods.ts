/**
 * The page: the tree that an extension reads, and the scripts that it adds.
 *
 * A client script is the only extension write that stays after the editor
 * closes and runs for a visitor. `builder/extension_page.py` has the reasons
 * and the owner rules. This file has two rules that the server cannot apply.
 * The page is the open page. Builder asks the user before a new script.
 *
 * The snapshot does not have the tree on purpose. The tree is large and it
 * changes on each key press. So an extension asks for it. `block.get` gives
 * one node to an extension that needs only one.
 *
 * The tree comes from the canvas, not from `pageStore.pageBlocks`, for two
 * reasons. Undo replaces the root instance, so `pageBlocks` is old after the
 * first undo. Also, `block.get` and `block.update` find blocks in the canvas.
 * A different tree would give ids that those two methods cannot find.
 *
 * When the user edits a component, the canvas has that fragment, not the page.
 * So this returns the fragment. The other choice gives ids that an extension
 * cannot use. `context.editingMode` tells which tree it is.
 */

import usePageStore from "@/stores/pageStore";
import useCanvasStore from "@/stores/canvasStore";
import { getBlockObject } from "@/utils/helpers";
import { createResource } from "frappe-ui";
import type { InstalledExtension } from "frappe-builder-extension-sdk/types";
import { confirmPageScript } from "../data/confirmations";
import type { MethodTable } from "../bridge/permissions";
import { fields, oneOf, refuse, text } from "../bridge/params";

/**
 * A list, because Builder stores a page as a list. Today the list always has
 * one root.
 *
 * With no canvas, the call is refused. It does not return an empty list. So an
 * extension that calls before the editor is ready can tell this from an empty page.
 */
const getBlocks = () => {
	const root = useCanvasStore().activeCanvas?.getRootBlock();
	if (!root) throw refuse("No canvas is open.", "no_canvas");
	return [getBlockObject(root)];
};

const SCRIPT_TYPES = ["JavaScript", "CSS"] as const;

/** A plain copy, because `createResource` returns its reactive `data`. */
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
 * A script always goes to the open page.
 *
 * If an extension could name a page, it could add code to a page that nobody
 * sees. Also, the confirmation would name a route that the user does not see.
 */
const openPage = () => {
	const page = usePageStore().activePage;
	if (!page) throw refuse("No page is open.", "no_page");
	return page;
};

const readScriptType = (params: unknown) => oneOf(fields(params).type, SCRIPT_TYPES, "type");

/**
 * Makes the script of that type for this extension on the open page, or
 * replaces the existing script.
 *
 * Builder asks the user only before a new script. The question is if this
 * extension can run code on this page. A new version of the same script does
 * not change that answer.
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
	"page.getBlocks": { needs: null, run: getBlocks },
	"page.attachScript": { needs: "page.write", run: attachScript },
	"page.detachScript": { needs: "page.write", run: detachScript },
	// these are its own scripts. So the permission that wrote them also reads them
	"page.listScripts": { needs: "page.write", run: listScripts },
};
