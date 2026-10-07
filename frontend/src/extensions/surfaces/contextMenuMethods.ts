/**
 * Context menu rows.
 *
 * All other surfaces check their rule against the selection. This surface
 * checks it against the block that the user right-clicked. When more than one
 * block is selected, that block can be different. So the host checks a rule
 * here for each block, when it shows the row under the cursor.
 *
 * `condition` and `disabled` both get the menu context (see `ContextMenu.vue`).
 * So `showWhen` and `enableWhen` use fields that already exist.
 *
 * `menu` is not a condition. It never changes after registration. It names the
 * menu of the row, and the host adds it to the same check.
 */

import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import type { BlockMenuContext, ContextMenuOption } from "@/types/blockContextMenu";
import { editorContext, getBlockSnapshot } from "../context/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../context/showWhen";
import type { MethodTable } from "../bridge/permissions";
import type { EditorContext } from "frappe-builder-extension-sdk/types";
import { invokeAction } from "./actionMethods";
import { fields, flag, oneOf, optionalText, text } from "../bridge/params";
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
		// a row with no action does nothing on a click
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

/** The snapshot. The clicked block gives the block fields of the selection. */
const contextFor = (menu: BlockMenuContext): EditorContext => {
	const snapshot = editorContext.value;
	// count and blockIds still describe the real selection. Only the block snapshot changes
	return { ...snapshot, selection: { ...snapshot.selection, ...getBlockSnapshot(menu.block) } };
};

/**
 * The data that goes through the port. `target` is a DOM node, and `block` is a
 * class instance. Neither can go through a port. The extension gets an id, and
 * asks for more with `block.get(blockId)`.
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
	// the host shows the row and runs the action through the bridge
	"contextMenu.register": { needs: null, run: rows.register },
	"contextMenu.unregister": { needs: null, run: rows.unregister },
	"contextMenu.update": { needs: null, run: rows.update },
};
