/**
 * Context menu rows. The surface D20 was written for.
 *
 * Every other surface asks its rule about the selection. This one asks about the
 * block the user right-clicked, which is a different block whenever more than
 * one is selected. A rule here is therefore answered per block, at render, for
 * the row under the cursor — the property that makes rules worth having.
 *
 * `condition` and `disabled` both receive the menu context (`ContextMenu.vue:15`
 * and `:18`), so the two halves of D20 land on fields that already exist.
 *
 * `menu` is not a condition. It never changes after registration, so it says
 * which menu the row belongs to and the host folds it into the same expression.
 */

import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import type { BlockMenuContext, ContextMenuOption } from "@/types/blockContextMenu";
import { editorContext, factsFor } from "../editor/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../editor/showWhen";
import type { MethodTable } from "../host/capabilities";
import type { EditorContext } from "frappe-builder-extension-sdk/types";
import { invokeAction } from "./actionMethods";
import { fields, flag, oneOf, optionalText, text } from "../params";
import { createSurfaceItems, type SurfaceItem } from "./surfaceItems";

const MENUS = ["canvas", "layers", "both"] as const;

type Menu = (typeof MENUS)[number];

type Registration = {
	name: string;
	label: string;
	action: string;
	menu: Menu;
	before?: string;
	after?: string;
	showWhen?: ShowWhenRule;
	enableWhen?: ShowWhenRule;
	visible: boolean;
	enabled: boolean;
};

const readRegistration = (params: unknown): Registration => {
	const sent = fields(params);
	assertRule(sent.showWhen as ShowWhenRule | undefined);
	assertRule(sent.enableWhen as ShowWhenRule | undefined, "enableWhen");

	return {
		name: text(sent.name, "name"),
		label: text(sent.label, "label"),
		// a row with nothing to run is a row that does nothing when clicked
		action: text(sent.action, "action"),
		menu: sent.menu === undefined ? "both" : oneOf(sent.menu, MENUS, "menu"),
		before: optionalText(sent.before, "before"),
		after: optionalText(sent.after, "after"),
		showWhen: sent.showWhen as ShowWhenRule | undefined,
		enableWhen: sent.enableWhen as ShowWhenRule | undefined,
		visible: true,
		enabled: true,
	};
};

const mergeRegistration = (current: Registration, patch: Record<string, unknown>): Registration => ({
	...current,
	label: optionalText(patch.label, "label") ?? current.label,
	visible: flag(patch.visible, current.visible),
	enabled: flag(patch.enabled, current.enabled),
});

const inMenu = (menu: Menu, fromLayersPanel: boolean) =>
	menu === "both" || (menu === "layers") === fromLayersPanel;

/** The snapshot, with the clicked block answering for the selection. */
const contextFor = (menu: BlockMenuContext): EditorContext => {
	const snapshot = editorContext.value;
	// count and blockIds still describe the real selection: only the block facts move
	return { ...snapshot, selection: { ...snapshot.selection, ...factsFor(menu.block) } };
};

/**
 * What crosses the port. `target` is a DOM node and `block` is a class
 * instance, so neither can travel. The extension receives an id and asks for
 * more with `block.get(blockId)`.
 */
const portable = (menu: BlockMenuContext) => ({
	blockId: menu.block.blockId,
	fromLayersPanel: menu.fromLayersPanel,
});

const toRegistryItem = (key: string, { extension, registration }: SurfaceItem<Registration>): ContextMenuOption => ({
	name: key,
	label: registration.label,
	before: registration.before,
	after: registration.after,
	action: (menu) => void invokeAction(extension, registration.action, portable(menu)),
	condition: (menu) =>
		inMenu(registration.menu, menu.fromLayersPanel) &&
		registration.visible &&
		matches(registration.showWhen, contextFor(menu)),
	disabled: (menu) => !registration.enabled || !matches(registration.enableWhen, contextFor(menu)),
});

const rows = createSurfaceItems<Registration, ContextMenuOption>({
	kind: "context menu item",
	registry: blockContextMenuOptions,
	readRegistration,
	mergeRegistration,
	toRegistryItem,
});

export const contextMenuMethods: MethodTable = {
	// the host draws the row and runs the action through the bridge
	"contextMenu.register": { needs: null, run: rows.register },
	"contextMenu.unregister": { needs: null, run: rows.unregister },
	"contextMenu.update": { needs: null, run: rows.update },
};
