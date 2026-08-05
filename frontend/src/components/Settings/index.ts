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
};

// the sidebar renders groups in this order
export const settingsGroups: SettingsGroup[] = ["Current Page", "Global"];

export const settingsItems = createRegistry<SettingsItem>();

/**
 * The panes load on demand, so a surface that only reads the metadata, as the
 * command palette does, never pulls them into its chunk.
 *
 * A name doubles as the persisted settingsActiveTab value, so it must not change.
 */
const items: SettingsItem[] = [
	{
		name: "page_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Current Page",
		component: defineAsyncComponent(() => import("@/components/Settings/PageGeneral.vue")),
	},
	{
		name: "page_code",
		label: "Code",
		title: "Page Code",
		icon: "lucide-code",
		group: "Current Page",
		component: defineAsyncComponent(() => import("@/components/Settings/PageCode.vue")),
	},
	{
		name: "page_meta",
		label: "Meta",
		title: "Meta",
		icon: "lucide-square-dashed-bottom-code",
		group: "Current Page",
		component: defineAsyncComponent(() => import("@/components/Settings/PageMeta.vue")),
	},
	{
		name: "page_analytics",
		label: "Analytics",
		title: "Page Analytics",
		icon: "lucide-chart-bar",
		group: "Current Page",
		component: defineAsyncComponent(() => import("@/components/Settings/PageAnalytics.vue")),
	},
	{
		name: "global_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalGeneral.vue")),
	},
	{
		name: "global_users",
		label: "Users",
		title: "Users",
		icon: "lucide-users",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalUsers.vue")),
	},
	{
		name: "global_code",
		label: "Code",
		title: "Global Code",
		icon: "lucide-code",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalCode.vue")),
	},
	{
		name: "global_redirects",
		label: "Redirects",
		title: "Redirects",
		icon: "lucide-shuffle",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalRedirects.vue")),
	},
	{
		name: "global_robots",
		label: "Robots",
		title: "Robots.txt",
		icon: "lucide-bot",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/PageRobots.vue")),
	},
	{
		name: "global_domains",
		label: "Domains",
		title: "Custom Domains",
		icon: "lucide-globe",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalDomains.vue")),
		condition: () => Boolean(window.is_fc_site || window.is_developer_mode),
	},
	{
		name: "global_analytics",
		label: "Analytics",
		title: "Site Analytics",
		icon: "lucide-chart-bar",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalAnalytics.vue")),
	},
	{
		name: "global_developer",
		label: "Developer",
		title: "Developer Settings",
		icon: "lucide-terminal",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalDeveloper.vue")),
	},
	{
		name: "global_ai",
		label: "AI",
		title: "AI Settings",
		icon: "lucide-sparkles",
		group: "Global",
		component: defineAsyncComponent(() => import("@/components/Settings/GlobalAI.vue")),
	},
];

export function registerSettingsItems() {
	items.forEach(settingsItems.register);
}
