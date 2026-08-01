import GlobalAI from "@/components/Settings/GlobalAI.vue";
import GlobalAnalytics from "@/components/Settings/GlobalAnalytics.vue";
import GlobalCode from "@/components/Settings/GlobalCode.vue";
import GlobalDeveloper from "@/components/Settings/GlobalDeveloper.vue";
import GlobalDomains from "@/components/Settings/GlobalDomains.vue";
import GlobalGeneral from "@/components/Settings/GlobalGeneral.vue";
import GlobalRedirects from "@/components/Settings/GlobalRedirects.vue";
import GlobalUsers from "@/components/Settings/GlobalUsers.vue";
import PageAnalytics from "@/components/Settings/PageAnalytics.vue";
import PageCode from "@/components/Settings/PageCode.vue";
import PageGeneral from "@/components/Settings/PageGeneral.vue";
import PageMeta from "@/components/Settings/PageMeta.vue";
import PageRobots from "@/components/Settings/PageRobots.vue";
import { settingsPanes, type SettingsPane } from "@/components/Settings/panes";
import { createRegistry } from "@/utils/createRegistry";
import type { Component } from "vue";

export { settingsGroups } from "@/components/Settings/panes";
export type { SettingsGroup, SettingsPane } from "@/components/Settings/panes";

export type SettingsItem = SettingsPane & {
	component: Component;
};

const paneComponents: Record<string, Component> = {
	page_general: PageGeneral,
	page_code: PageCode,
	page_meta: PageMeta,
	page_analytics: PageAnalytics,
	global_general: GlobalGeneral,
	global_users: GlobalUsers,
	global_code: GlobalCode,
	global_redirects: GlobalRedirects,
	global_robots: PageRobots,
	global_domains: GlobalDomains,
	global_analytics: GlobalAnalytics,
	global_developer: GlobalDeveloper,
	global_ai: GlobalAI,
};

export const settingsItems = createRegistry<SettingsItem>();
export const registerSettingsItem = settingsItems.register;

export function registerBuiltInSettingsItems() {
	settingsPanes.forEach((pane) =>
		registerSettingsItem({ ...pane, component: paneComponents[pane.name] }),
	);
}
