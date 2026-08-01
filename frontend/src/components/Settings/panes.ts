export type SettingsGroup = "Current Page" | "Global";

export type SettingsPane = {
	name: string;
	label: string;
	title: string;
	icon: string;
	group: SettingsGroup;
	rank: number;
	disabled?: boolean;
	condition?: () => boolean;
};

// the sidebar renders groups in this order
export const settingsGroups: SettingsGroup[] = ["Current Page", "Global"];

/**
 * Metadata only, with no pane components. The command palette imports this to
 * list the settings pages without pulling the panes into its chunk.
 *
 * A name doubles as the persisted settingsActiveTab value, so it must not change.
 */
export const settingsPanes: SettingsPane[] = [
	{
		name: "page_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Current Page",
		rank: 10,
	},
	{
		name: "page_code",
		label: "Code",
		title: "Page Code",
		icon: "lucide-code",
		group: "Current Page",
		rank: 20,
	},
	{
		name: "page_meta",
		label: "Meta",
		title: "Meta",
		icon: "lucide-square-dashed-bottom-code",
		group: "Current Page",
		rank: 30,
	},
	{
		name: "page_analytics",
		label: "Analytics",
		title: "Page Analytics",
		icon: "lucide-chart-bar",
		group: "Current Page",
		rank: 40,
	},
	{
		name: "global_general",
		label: "General",
		title: "General",
		icon: "lucide-settings",
		group: "Global",
		rank: 110,
		disabled: false,
	},
	{
		name: "global_users",
		label: "Users",
		title: "Users",
		icon: "lucide-users",
		group: "Global",
		rank: 120,
	},
	{
		name: "global_code",
		label: "Code",
		title: "Global Code",
		icon: "lucide-code",
		group: "Global",
		rank: 130,
	},
	{
		name: "global_redirects",
		label: "Redirects",
		title: "Redirects",
		icon: "lucide-shuffle",
		group: "Global",
		rank: 140,
	},
	{
		name: "global_robots",
		label: "Robots",
		title: "Robots.txt",
		icon: "lucide-bot",
		group: "Global",
		rank: 150,
	},
	{
		name: "global_domains",
		label: "Domains",
		title: "Custom Domains",
		icon: "lucide-globe",
		group: "Global",
		rank: 160,
		condition: () => Boolean(window.is_fc_site || window.is_developer_mode),
	},
	{
		name: "global_analytics",
		label: "Analytics",
		title: "Site Analytics",
		icon: "lucide-chart-bar",
		group: "Global",
		rank: 170,
	},
	{
		name: "global_developer",
		label: "Developer",
		title: "Developer Settings",
		icon: "lucide-terminal",
		group: "Global",
		rank: 180,
	},
	{
		name: "global_ai",
		label: "AI",
		title: "AI Settings",
		icon: "lucide-sparkles",
		group: "Global",
		rank: 190,
	},
];
