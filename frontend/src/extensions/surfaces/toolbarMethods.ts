/**
 * Toolbar buttons. The extension sends a descriptor, and Builder shows its own `Button`.
 * Read-only mode does not disable a button. Use `enableWhen: { readOnly: false }`.
 */

import ExtensionToolbarButton from "@/components/ToolbarItems/ExtensionToolbarButton.vue";
import { toolbarItems, type ToolbarItem, type ToolbarRegion } from "@/components/ToolbarItems";
import { editorContext } from "../context/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../context/showWhen";
import type { MethodTable } from "../bridge/permissions";
import { invokeAction } from "./actionMethods";
import { fields, flag, oneOf, optionalText, text } from "../bridge/params";
import { createSurfaceItems, type SurfaceItem } from "./surfaceItems";

const REGIONS = ["left", "center", "right"] as const;

type Registration = {
	name: string;
	region: ToolbarRegion;
	icon: string;
	label?: string;
	tooltip?: string;
	action?: string;
	badge?: string | number | null;
	before?: string;
	after?: string;
	showWhen?: ShowWhenRule;
	enableWhen?: ShowWhenRule;
	visible: boolean;
	enabled: boolean;
};

const badgeOf = (value: unknown) =>
	typeof value === "string" || typeof value === "number" ? value : null;

const readRegistration = (params: unknown): Registration => {
	const sent = fields(params);
	assertRule(sent.showWhen as ShowWhenRule | undefined);
	assertRule(sent.enableWhen as ShowWhenRule | undefined, "enableWhen");

	return {
		name: text(sent.name, "name"),
		region: oneOf(sent.region, REGIONS, "region"),
		icon: text(sent.icon, "icon"),
		label: optionalText(sent.label, "label"),
		tooltip: optionalText(sent.tooltip, "tooltip"),
		action: optionalText(sent.action, "action"),
		badge: badgeOf(sent.badge),
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
	icon: optionalText(patch.icon, "icon") ?? current.icon,
	label: optionalText(patch.label, "label") ?? current.label,
	tooltip: optionalText(patch.tooltip, "tooltip") ?? current.tooltip,
	badge: "badge" in patch ? badgeOf(patch.badge) : current.badge,
	visible: flag(patch.visible, current.visible),
	enabled: flag(patch.enabled, current.enabled),
});

const toRegistryItem = (key: string, { extension, registration }: SurfaceItem<Registration>): ToolbarItem => ({
	name: key,
	region: registration.region,
	isExtension: true,
	before: registration.before,
	after: registration.after,
	component: ExtensionToolbarButton,
	props: () => ({
		icon: registration.icon,
		label: registration.label,
		tooltip: registration.tooltip,
		badge: registration.badge,
		disabled: !registration.enabled || !matches(registration.enableWhen, editorContext.value),
		onClick: registration.action
			? () => void invokeAction(extension, registration.action as string)
			: undefined,
	}),
	condition: () => matches(registration.showWhen, editorContext.value) && registration.visible,
});

const buttons = createSurfaceItems<Registration, ToolbarItem>({
	kind: "toolbar item",
	registry: toolbarItems,
	readRegistration,
	mergeRegistration,
	toRegistryItem,
});

export const toolbarMethods: MethodTable = {
	// Builder shows the button. So the extension gets no new access.
	"toolbar.register": { needs: null, run: buttons.register },
	"toolbar.unregister": { needs: null, run: buttons.unregister },
	"toolbar.update": { needs: null, run: buttons.update },
};
