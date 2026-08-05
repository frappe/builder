import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import { defineAsyncComponent, type Component } from "vue";

export type SettingsGroup = "Current Page" | "Global";

export type SettingsItem = RegistryItem & {
	label: string;
	title: string;
	icon: string;
	group: SettingsGroup;
	component: Component;
	disabled?: boolean;
	/** an async pane exposes its loader, so prefetch can warm it while the editor idles */
	load?: () => Promise<unknown>;
};

/** a pane declares the loader once: register builds the component from it */
type SettingsPane = Omit<SettingsItem, "component"> & { load: () => Promise<{ default: Component }> };

// the sidebar renders groups in this order
export const settingsGroups: SettingsGroup[] = ["Current Page", "Global"];

export const settingsItems = createRegistry<SettingsItem>();

/**
 * Registered at module load, so every surface reads the same list however it
 * opens. The panes load on demand, so a surface that only reads the metadata,
 * as the command palette does, never pulls them into its chunk.
 *
 * A name doubles as the persisted settingsActiveTab value, so it must not change.
 */
const panes: SettingsPane[] = [
	{
		name: "page_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Current Page",
		load: () => import("@/components/Settings/PageGeneral.vue"),
	},
	{
		name: "page_code",
		label: "Code",
		title: "Page Code",
		icon: "lucide-code",
		group: "Current Page",
		load: () => import("@/components/Settings/PageCode.vue"),
	},
	{
		name: "page_meta",
		label: "Meta",
		title: "Meta",
		icon: "lucide-square-dashed-bottom-code",
		group: "Current Page",
		load: () => import("@/components/Settings/PageMeta.vue"),
	},
	{
		name: "page_analytics",
		label: "Analytics",
		title: "Page Analytics",
		icon: "lucide-chart-bar",
		group: "Current Page",
		load: () => import("@/components/Settings/PageAnalytics.vue"),
	},
	{
		name: "global_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Global",
		load: () => import("@/components/Settings/GlobalGeneral.vue"),
	},
	{
		name: "global_users",
		label: "Users",
		title: "Users",
		icon: "lucide-users",
		group: "Global",
		load: () => import("@/components/Settings/GlobalUsers.vue"),
	},
	{
		name: "global_code",
		label: "Code",
		title: "Global Code",
		icon: "lucide-code",
		group: "Global",
		load: () => import("@/components/Settings/GlobalCode.vue"),
	},
	{
		name: "global_redirects",
		label: "Redirects",
		title: "Redirects",
		icon: "lucide-shuffle",
		group: "Global",
		load: () => import("@/components/Settings/GlobalRedirects.vue"),
	},
	{
		name: "global_robots",
		label: "Robots",
		title: "Robots.txt",
		icon: "lucide-bot",
		group: "Global",
		load: () => import("@/components/Settings/PageRobots.vue"),
	},
	{
		name: "global_domains",
		label: "Domains",
		title: "Custom Domains",
		icon: "lucide-globe",
		group: "Global",
		load: () => import("@/components/Settings/GlobalDomains.vue"),
		condition: () => Boolean(window.is_fc_site || window.is_developer_mode),
	},
	{
		name: "global_analytics",
		label: "Analytics",
		title: "Site Analytics",
		icon: "lucide-chart-bar",
		group: "Global",
		load: () => import("@/components/Settings/GlobalAnalytics.vue"),
	},
	{
		name: "global_developer",
		label: "Developer",
		title: "Developer Settings",
		icon: "lucide-terminal",
		group: "Global",
		load: () => import("@/components/Settings/GlobalDeveloper.vue"),
	},
	{
		name: "global_ai",
		label: "AI",
		title: "AI Settings",
		icon: "lucide-sparkles",
		group: "Global",
		load: () => import("@/components/Settings/GlobalAI.vue"),
	},
];

panes.forEach((pane) =>
	settingsItems.register({ ...pane, component: defineAsyncComponent(pane.load) }),
);

// warmed on idle by prefetchBuilderSettings, so the first open never waits on a chunk
export const preloadSettingsPanes = () =>
	settingsItems.visible.value.forEach((item) => item.load?.());
