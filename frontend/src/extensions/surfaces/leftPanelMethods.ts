/**
 * One left panel tab for each extension, shown as a frame (Tier C).
 *
 * The registry gets the same object shape as a built-in tab. So
 * `BuilderLeftPanel.vue` needs no code about extensions.
 */

import ExtensionFrame from "@/extensions/components/ExtensionFrame.vue";
import { leftPanelTabs, type LeftPanelTab } from "@/components/LeftPanelTabs";
import { editorContext } from "../context/editorContext";
import { assertRule, matches, type ShowWhenRule } from "../context/showWhen";
import { bridge } from "../bridge/bridge";
import type { MethodTable } from "../bridge/permissions";
import type { PortChannel } from "frappe-builder-extension-sdk/transport";
import { fields, flag, optionalText, text } from "../bridge/params";
import { createSurfaceItems, type SurfaceItem } from "./surfaceItems";

type Registration = {
	name: string;
	label: string;
	icon: string;
	before?: string;
	after?: string;
	showWhen?: ShowWhenRule;
	visible: boolean;
};

const readRegistration = (params: unknown): Registration => {
	const sent = fields(params);
	assertRule(sent.showWhen as ShowWhenRule | undefined);

	return {
		name: text(sent.name, "name"),
		label: text(sent.label, "label"),
		icon: text(sent.icon, "icon"),
		before: optionalText(sent.before, "before"),
		after: optionalText(sent.after, "after"),
		showWhen: sent.showWhen as ShowWhenRule | undefined,
		visible: true,
	};
};

const mergeRegistration = (current: Registration, patch: Record<string, unknown>): Registration => ({
	...current,
	label: optionalText(patch.label, "label") ?? current.label,
	icon: optionalText(patch.icon, "icon") ?? current.icon,
	visible: flag(patch.visible, current.visible),
});

const toRegistryItem = (key: string, { extension, registration }: SurfaceItem<Registration>): LeftPanelTab => {
	const requestHandler = bridge.requestHandlerFor(extension);

	return {
		name: key,
		label: registration.label,
		icon: registration.icon,
		usesRuntimeIcon: registration.icon.startsWith("lucide-"),
		before: registration.before,
		after: registration.after,
		// mount on the first open. After that, v-show keeps the document alive
		lazy: true,
		component: ExtensionFrame,
		props: () => ({
			extension: extension.name,
			slot: "panel",
			requestHandler,
			onConnect: (channel: PortChannel) => bridge.connect(extension.name, channel),
			onDisconnect: (channel: PortChannel) => bridge.disconnect(extension.name, channel),
		}),
		condition: () => matches(registration.showWhen, editorContext.value) && registration.visible,
	};
};

const tabs = createSurfaceItems<Registration, LeftPanelTab>({
	kind: "left panel tab",
	registry: leftPanelTabs,
	limitToOnePerExtension: true,
	readRegistration,
	mergeRegistration,
	toRegistryItem,
});

export const leftPanelMethods: MethodTable = {
	// the host shows the tab strip and mounts the frame. So no permission gates this
	"leftPanel.register": { needs: null, run: tabs.register },
	"leftPanel.unregister": { needs: null, run: tabs.unregister },
	"leftPanel.update": { needs: null, run: tabs.update },
};
