/**
 * One page in the settings dialog per extension, rendered as a frame
 * (Tier C). The same shape as the left panel tab. What differs is only where
 * the host puts it.
 *
 * The group is always "Global". `settingsGroups` is a fixed list of two, and
 * "Current Page" is about the page being edited, which an extension's own page
 * is not. There is no `settings.registerGroup`: a third group is a Builder
 * decision.
 */

import ExtensionFrame from "@/components/ExtensionFrame.vue";
import { settingsItems, type SettingsItem } from "@/components/Settings";
import { bridge } from "../host/bridge";
import type { MethodTable } from "../host/capabilities";
import type { PortChannel } from "frappe-builder-extension-sdk/transport";
import { fields, flag, optionalText, text } from "../params";
import { createSurfaceItems, type SurfaceItem } from "./surfaceItems";

type Registration = {
	name: string;
	label: string;
	title: string;
	icon: string;
	before?: string;
	after?: string;
	visible: boolean;
};

const readRegistration = (params: unknown): Registration => {
	const sent = fields(params);
	const label = text(sent.label, "label");

	return {
		name: text(sent.name, "name"),
		label,
		// the sidebar entry and the heading may differ, as the built-in panes show
		title: optionalText(sent.title, "title") ?? label,
		icon: text(sent.icon, "icon"),
		before: optionalText(sent.before, "before"),
		after: optionalText(sent.after, "after"),
		visible: true,
	};
};

const mergeRegistration = (current: Registration, patch: Record<string, unknown>): Registration => ({
	...current,
	label: optionalText(patch.label, "label") ?? current.label,
	title: optionalText(patch.title, "title") ?? current.title,
	icon: optionalText(patch.icon, "icon") ?? current.icon,
	visible: flag(patch.visible, current.visible),
});

const toRegistryItem = (key: string, { extension, registration }: SurfaceItem<Registration>): SettingsItem => {
	const dispatch = bridge.dispatcherFor(extension);

	return {
		name: key,
		label: registration.label,
		title: registration.title,
		icon: registration.icon,
		usesRuntimeIcon: registration.icon.startsWith("lucide-"),
		group: "Global",
		before: registration.before,
		after: registration.after,
		component: ExtensionFrame,
		// the dialog renders only the selected pane, so the frame mounts on first open
		props: () => ({
			extension: extension.name,
			slot: "settings",
			dispatch,
			onConnect: (channel: PortChannel) => bridge.connect(extension.name, channel),
			onDisconnect: (channel: PortChannel) => bridge.disconnect(extension.name, channel),
		}),
		condition: () => registration.visible,
	};
};

const pages = createSurfaceItems<Registration, SettingsItem>({
	kind: "settings item",
	registry: settingsItems,
	limitToOnePerExtension: true,
	readRegistration,
	mergeRegistration,
	toRegistryItem,
});

export const settingsMethods: MethodTable = {
	// the host draws the sidebar entry and mounts the frame, so no capability gates this
	"settings.registerItem": { needs: null, run: pages.register },
	"settings.unregisterItem": { needs: null, run: pages.unregister },
	"settings.update": { needs: null, run: pages.update },
};
