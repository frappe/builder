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
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component } from "vue";

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
export const registerSettingsItem = settingsItems.register;

// name doubles as the persisted settingsActiveTab value, so it must not change
export function registerBuiltInSettingsItems() {
	registerSettingsItem({
		name: "page_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Current Page",
		rank: 10,
		component: PageGeneral,
	});

	registerSettingsItem({
		name: "page_code",
		label: "Code",
		title: "Page Code",
		icon: "lucide-code",
		group: "Current Page",
		rank: 20,
		component: PageCode,
	});

	registerSettingsItem({
		name: "page_meta",
		label: "Meta",
		title: "Meta",
		icon: "lucide-square-dashed-bottom-code",
		group: "Current Page",
		rank: 30,
		component: PageMeta,
	});

	registerSettingsItem({
		name: "page_analytics",
		label: "Analytics",
		title: "Page Analytics",
		icon: "lucide-chart-bar",
		group: "Current Page",
		rank: 40,
		component: PageAnalytics,
	});

	registerSettingsItem({
		name: "global_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Global",
		rank: 110,
		component: GlobalGeneral,
		disabled: false,
	});

	registerSettingsItem({
		name: "global_users",
		label: "Users",
		title: "Users",
		icon: "lucide-users",
		group: "Global",
		rank: 120,
		component: GlobalUsers,
	});

	registerSettingsItem({
		name: "global_code",
		label: "Code",
		title: "Global Code",
		icon: "lucide-code",
		group: "Global",
		rank: 130,
		component: GlobalCode,
	});

	registerSettingsItem({
		name: "global_redirects",
		label: "Redirects",
		title: "Redirects",
		icon: "lucide-shuffle",
		group: "Global",
		rank: 140,
		component: GlobalRedirects,
	});

	registerSettingsItem({
		name: "global_robots",
		label: "Robots",
		title: "Robots.txt",
		icon: "lucide-bot",
		group: "Global",
		rank: 150,
		component: PageRobots,
	});

	registerSettingsItem({
		name: "global_domains",
		label: "Domains",
		title: "Custom Domains",
		icon: "lucide-globe",
		group: "Global",
		rank: 160,
		component: GlobalDomains,
		condition: () => Boolean(window.is_fc_site || window.is_developer_mode),
	});

	registerSettingsItem({
		name: "global_analytics",
		label: "Analytics",
		title: "Site Analytics",
		icon: "lucide-chart-bar",
		group: "Global",
		rank: 170,
		component: GlobalAnalytics,
	});

	registerSettingsItem({
		name: "global_developer",
		label: "Developer",
		title: "Developer Settings",
		icon: "lucide-terminal",
		group: "Global",
		rank: 180,
		component: GlobalDeveloper,
	});

	registerSettingsItem({
		name: "global_ai",
		label: "AI",
		title: "AI Settings",
		icon: "lucide-sparkles",
		group: "Global",
		rank: 190,
		component: GlobalAI,
	});
}
