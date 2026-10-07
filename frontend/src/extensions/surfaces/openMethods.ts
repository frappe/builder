/**
 * What Builder opens when the user opens an extension from its details pane.
 *
 * The target names a UI that the extension registered in a different call:
 * its popover, its dialog or its left panel tab. So this file shows no window
 * of its own. An extension declares one target or none. With none, it gets no
 * Open button.
 *
 * Builder starts the frame, not the extension. So no permission gates this.
 * The user clicked a button in Builder, and the extension asked for nothing.
 * This file follows `actionMethods.ts`, not `createSurfaceItems`: one target
 * for each extension, no registry item and no order.
 */

import { leftPanelTabs } from "@/components/LeftPanelTabs";
import useBuilderStore from "@/stores/builderStore";
import type { InstalledExtension, OpenTarget } from "frappe-builder-extension-sdk/types";
import { reactive } from "vue";
import { startDialog, startPopover } from "../editor/uiMethods";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import { fields, oneOf, optionalText, optionalWholeNumber, refuse, text } from "../bridge/params";

const kinds = ["popover", "dialog", "leftPanel"] as const;

/** Reactive. The details pane shows its Open button from this. */
export const openTargets = reactive(new Map<string, OpenTarget>());

const readTarget = (params: unknown): OpenTarget => {
	const sent = fields(params);
	const kind = oneOf(sent.kind, kinds, "kind");

	if (kind === "leftPanel") return { kind, name: text(sent.name, "name") };
	if (kind === "dialog") return { kind, title: optionalText(sent.title, "title") };
	return {
		kind,
		width: optionalWholeNumber(sent.width, "width"),
		height: optionalWholeNumber(sent.height, "height"),
	};
};

const register = (params: unknown, extension: InstalledExtension) => {
	const target = readTarget(params);
	// a second registration replaces the target. Do not add its teardown two times
	if (!openTargets.has(extension.name)) {
		bridge.registerTeardown(extension.name, () => openTargets.delete(extension.name));
	}
	openTargets.set(extension.name, target);
};

const unregister = (params: unknown, extension: InstalledExtension) => {
	if (!openTargets.delete(extension.name)) {
		throw refuse(`"${extension.name}" has no open target to unregister.`, "unknown_item");
	}
};

/** The registry name that `createItemKey` in `surfaceItems.ts` gave the tab of this extension. */
const tabKey = (extension: InstalledExtension, name: string) => `${extension.name}:${name}`;

/**
 * True if the details pane can open this extension.
 *
 * A left panel target must name a visible tab. `leftPanel.update` and a
 * `showWhen` rule can both hide a tab. A button that opens nothing is worse
 * than no button.
 */
export const canOpen = (extension: InstalledExtension) => {
	const target = openTargets.get(extension.name);
	if (!target) return false;
	if (target.kind !== "leftPanel") return true;
	return leftPanelTabs.visible.value.some((tab) => tab.name === tabKey(extension, target.name));
};

/** Opens the declared target. The pane calls this only when `canOpen` is true. */
export const openExtension = (extension: InstalledExtension) => {
	const target = openTargets.get(extension.name);
	if (!target) return;

	if (target.kind === "popover") {
		return void startPopover({ width: target.width, height: target.height }, extension);
	}
	if (target.kind === "dialog") return void startDialog({ title: target.title }, extension);

	// the same two writes as `select` in `BuilderLeftPanel.vue`. So Open goes to
	// the same place as a click on the tab
	const builderStore = useBuilderStore();
	builderStore.leftPanelActiveTab = tabKey(extension, target.name);
	builderStore.showTokenManager = false;
};

export const openMethods: MethodTable = {
	// Builder opens the target. So the extension needs no permission for it
	"open.register": { needs: null, run: register },
	"open.unregister": { needs: null, run: unregister },
};
