/**
 * What Builder opens when the user opens an extension from its details pane.
 *
 * The target names an interface the extension registered elsewhere — its
 * popover, its dialog, or its own left panel tab — so nothing here draws chrome
 * of its own. An extension declares one target or none, and an extension that
 * declared none gets no Open button.
 *
 * Builder starts the frame, not the extension, so no capability gates this. The
 * user pressed a button in Builder's own chrome and the extension asked for
 * nothing. `actionMethods.ts` is the shape this follows rather than
 * `createSurfaceItems`: one per extension, no registry item, and no ordering.
 */

import { leftPanelTabs } from "@/components/LeftPanelTabs";
import useBuilderStore from "@/stores/builderStore";
import type { InstalledExtension, OpenTarget } from "frappe-builder-extension-sdk/types";
import { reactive } from "vue";
import { startDialog, startPopover } from "../editor/uiMethods";
import { bridge } from "../host/bridge";
import type { MethodTable } from "../host/capabilities";
import { fields, oneOf, optionalText, optionalWholeNumber, refuse, text } from "../params";

const kinds = ["popover", "dialog", "leftPanel"] as const;

/** Reactive: the details pane paints its Open button from this. */
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
	// registering again replaces the target, so its teardown must not be added twice
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

/** The registry name `surfaceItems.ts:createItemKey` gave this extension's tab. */
const tabKey = (extension: InstalledExtension, name: string) => `${extension.name}:${name}`;

/**
 * Whether the details pane can offer this extension.
 *
 * A left panel target has to name a tab that is showing. Both `leftPanel.update`
 * and a `showWhen` rule can hide one, and a button that switches to nothing is
 * worse than no button at all.
 */
export const canOpen = (extension: InstalledExtension) => {
	const target = openTargets.get(extension.name);
	if (!target) return false;
	if (target.kind !== "leftPanel") return true;
	return leftPanelTabs.visible.value.some((tab) => tab.name === tabKey(extension, target.name));
};

/** Runs the declared target. The pane calls this only where `canOpen` is true. */
export const openExtension = (extension: InstalledExtension) => {
	const target = openTargets.get(extension.name);
	if (!target) return;

	if (target.kind === "popover") {
		return void startPopover({ width: target.width, height: target.height }, extension);
	}
	if (target.kind === "dialog") return void startDialog({ title: target.title }, extension);

	// the same two writes `BuilderLeftPanel.vue:select` makes, so Open lands the
	// user where clicking the tab would have
	const builderStore = useBuilderStore();
	builderStore.leftPanelActiveTab = tabKey(extension, target.name);
	builderStore.showTokenManager = false;
};

export const openMethods: MethodTable = {
	// Builder chrome opens the target, so the extension needs no grant for it
	"open.register": { needs: null, run: register },
	"open.unregister": { needs: null, run: unregister },
};
