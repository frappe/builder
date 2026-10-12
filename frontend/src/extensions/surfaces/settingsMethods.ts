/**
 * One page in the settings dialog for each extension, shown as a frame
 * (Tier C). It has the same shape as the left panel tab. Only its place is
 * different.
 *
 * The group is always "Global". `settingsGroups` is a fixed list of two.
 * "Current Page" is about the open page, and the page of an extension is not
 * that page. There is no `settings.registerGroup`. Builder decides if a third
 * group is necessary.
 */

import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { settingsItems, type SettingsItem } from "@/components/Settings";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import type { PortChannel } from "frappe-builder-extension-sdk/transport";
import { fields, flag, optionalText, text } from "../bridge/params";
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
		// the sidebar entry and the heading can be different, as in the built-in panes
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
	const requestHandler = bridge.requestHandlerFor(extension);

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
		// the dialog shows only the selected pane. So the frame mounts on the first open
		props: () => ({
			extension: extension.name,
			slot: "settings",
			requestHandler,
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
	// the host shows the sidebar entry and mounts the frame. So no permission gates this
	"settings.registerItem": { needs: null, run: pages.register },
	"settings.unregisterItem": { needs: null, run: pages.unregister },
	"settings.update": { needs: null, run: pages.update },
};
