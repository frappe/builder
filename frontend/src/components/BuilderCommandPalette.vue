<template>
	<CommandPalette
		v-model:show="show"
		v-model:searchQuery="searchQuery"
		:groups="commandGroups"
		:step-label="activeStep?.label"
		:placeholder="activeStep?.placeholder"
		:hint="activeStep?.hint"
		:loading="isSearching"
		@select="executeCommand"
		@back="handleBack" />
</template>

<script setup lang="ts">
import { searchablePages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { useDark, useToggle, watchDebounced } from "@vueuse/core";
import { useShortcut } from "frappe-ui";
import { computed, inject, nextTick, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import type { CommandPaletteItem as CPItem } from "./CommandPalette.vue";
import CommandPalette from "./CommandPalette.vue";
import CommandPaletteItem from "./CommandPaletteItem.vue";

const show = ref(false);
const searchQuery = ref("");
const activeStep = ref<{ id: string; label: string; placeholder: string; hint: string } | null>(null);

const builderStore = useBuilderStore();
const pageStore = usePageStore();
const route = useRoute();
const router = useRouter();
const showShortcuts = inject<() => void>("showShortcuts", () => {});

const isBuilderRoute = computed(() => route.name === "builder");

useShortcut({
	key: "k",
	ctrl: true,
	description: "Open Command Palette",
	group: "General",
	allowInInput: true,
	handler: () => {
		show.value = true;
	},
});

const isDark = useDark({ attribute: "data-theme" });
const toggleDark = useToggle(isDark);

const transitionTheme = () => {
	if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		document.startViewTransition(() => toggleDark());
	} else {
		toggleDark();
	}
};

function openSettings(tab: string) {
	builderStore.settingsActiveTab = tab;
	builderStore.showSettingsDialog = true;
}

interface Command extends CPItem {
	action: () => void;
	group: string;
}

interface SettingsCommand extends CPItem {
	action: () => void;
	section: "page" | "global";
}

const staticCommands = computed<Command[]>(() => {
	const isBuilder = isBuilderRoute.value;
	return [
		{
			name: "search-page",
			title: "Search Page",
			icon: "lucide-file-search",
			description: "Navigate",
			group: "Navigate",
			keepOpen: true,
			action: () => {
				activeStep.value = {
					id: "search-page",
					label: "Search Page",
					placeholder: "Search by name or route...",
					hint: "Start typing to search pages",
				};
				searchQuery.value = "";
			},
		},
		...(isBuilder
			? [
					{
						name: "go-to-dashboard",
						title: "Go to Dashboard",
						icon: "lucide-layout-dashboard",
						description: "Navigate",
						group: "Navigate",
						action: () => router.push({ name: "home" }),
					},
				]
			: []),
		...(isBuilder
			? [
					{
						name: "preview",
						title: "Preview Page",
						icon: "lucide-play",
						description: "Page",
						group: "Page",
						action: () => {
							if (pageStore.selectedPage) {
								router.push({ name: "preview", params: { pageId: pageStore.selectedPage } });
							}
						},
					},
					{
						name: "publish",
						title: "Publish Page",
						icon: "lucide-globe",
						description: "Page",
						group: "Page",
						action: () => pageStore.publishPage(),
					},
					{
						name: "duplicate-page",
						title: "Duplicate Page",
						icon: "lucide-copy-plus",
						description: "Page",
						group: "Page",
						action: () => {
							if (pageStore.activePage) {
								pageStore.duplicatePage(pageStore.activePage);
							}
						},
					},
				]
			: []),
		...(isBuilder
			? [
					{
						name: "expand-layers",
						title: "Expand All Layers",
						icon: "lucide-chevrons-up-down",
						description: "Layers",
						group: "Layers",
						action: async () => {
							builderStore.showLeftPanel = true;
							builderStore.leftPanelActiveTab = "Layers";
							await nextTick();
							builderStore.activeLayers?.expandAll();
						},
					},
					{
						name: "collapse-layers",
						title: "Collapse All Layers",
						icon: "lucide-chevrons-down-up",
						description: "Layers",
						group: "Layers",
						action: async () => {
							builderStore.showLeftPanel = true;
							builderStore.leftPanelActiveTab = "Layers";
							await nextTick();
							builderStore.activeLayers?.collapseAll();
						},
					},
				]
			: []),
		...(isBuilder
			? [
					{
						name: "toggle-left-panel",
						title: `${builderStore.showLeftPanel ? "Hide" : "Show"} Left Panel`,
						icon: builderStore.showLeftPanel ? "lucide-panel-left-close" : "lucide-panel-left-open",
						description: "View",
						group: "View",
						action: () => {
							builderStore.showLeftPanel = !builderStore.showLeftPanel;
						},
					},
					{
						name: "toggle-right-panel",
						title: `${builderStore.showRightPanel ? "Hide" : "Show"} Right Panel`,
						icon: builderStore.showRightPanel ? "lucide-panel-right-close" : "lucide-panel-right-open",
						description: "View",
						group: "View",
						action: () => {
							builderStore.showRightPanel = !builderStore.showRightPanel;
						},
					},
				]
			: []),
		{
			name: "toggle-theme",
			title: `Switch to ${isDark.value ? "Light" : "Dark"} Mode`,
			icon: isDark.value ? "lucide-sun" : "lucide-moon",
			description: "View",
			group: "View",
			action: () => transitionTheme(),
		},
		...(isBuilder
			? [
					{
						name: "shortcuts",
						title: "Keyboard Shortcuts",
						icon: "lucide-command",
						description: "General",
						group: "General",
						action: () => showShortcuts(),
					},
				]
			: []),
		{
			name: "settings",
			title: "Settings",
			icon: "lucide-settings-2",
			description: "General",
			group: "General",
			keepOpen: true,
			action: () => {
				activeStep.value = {
					id: "settings",
					label: "Settings",
					placeholder: "Search settings...",
					hint: "Browse all settings",
				};
				searchQuery.value = "";
			},
		},
	] as Command[];
});

const allSettingsCommands: SettingsCommand[] = [
	{
		name: "page_general",
		title: "General",
		description: "Settings",
		icon: "lucide-settings",
		section: "page",
		action: () => openSettings("page_general"),
	},
	{
		name: "page_code",
		title: "Page Code",
		description: "Settings",
		icon: "lucide-code",
		section: "page",
		action: () => openSettings("page_code"),
	},
	{
		name: "page_meta",
		title: "Meta",
		description: "Settings",
		icon: "lucide-square-dashed-bottom-code",
		section: "page",
		action: () => openSettings("page_meta"),
	},
	{
		name: "page_analytics",
		title: "Analytics",
		description: "Settings",
		icon: "lucide-chart-bar",
		section: "page",
		action: () => openSettings("page_analytics"),
	},
	// Global settings
	{
		name: "global_general",
		title: "General",
		description: "Settings",
		icon: "lucide-settings",
		section: "global",
		action: () => openSettings("global_general"),
	},
	{
		name: "global_code",
		title: "Global Code",
		description: "Settings",
		icon: "lucide-code",
		section: "global",
		action: () => openSettings("global_code"),
	},
	{
		name: "global_redirects",
		title: "Redirects",
		description: "Settings",
		icon: "lucide-shuffle",
		section: "global",
		action: () => openSettings("global_redirects"),
	},
	{
		name: "global_analytics",
		title: "Site Analytics",
		description: "Settings",
		icon: "lucide-chart-bar",
		section: "global",
		action: () => openSettings("global_analytics"),
	},
	{
		name: "global_developer",
		title: "Developer",
		description: "Settings",
		icon: "lucide-terminal",
		section: "global",
		action: () => openSettings("global_developer"),
	},
	{
		name: "global_ai",
		title: "AI",
		description: "Settings",
		icon: "lucide-sparkles",
		section: "global",
		action: () => openSettings("global_ai"),
	},
];

const settingsCommands = computed<SettingsCommand[]>(() =>
	isBuilderRoute.value ? allSettingsCommands : allSettingsCommands.filter((c) => c.section === "global"),
);

const RECENT_COMMANDS_KEY = "builder:recent_commands";
const RECENT_PAGES_KEY = "builder:recent_pages";

function getRecentCommandNames(): string[] {
	try {
		return JSON.parse(localStorage.getItem(RECENT_COMMANDS_KEY) || "[]");
	} catch {
		return [];
	}
}

const recentCommandNames = ref<string[]>(getRecentCommandNames());

function trackRecentCommand(name: string) {
	const recent = recentCommandNames.value.filter((n) => n !== name);
	recent.unshift(name);
	recentCommandNames.value = recent.slice(0, 5);
	localStorage.setItem(RECENT_COMMANDS_KEY, JSON.stringify(recentCommandNames.value));
}

const recentCommands = computed<(Command | SettingsCommand)[]>(() => {
	const all = [...staticCommands.value, ...settingsCommands.value] as (Command | SettingsCommand)[];
	return recentCommandNames.value.map((name) => all.find((c) => c.name === name)).filter(Boolean) as (
		| Command
		| SettingsCommand
	)[];
});

function getRecentPageNames(): string[] {
	try {
		return JSON.parse(localStorage.getItem(RECENT_PAGES_KEY) || "[]");
	} catch {
		return [];
	}
}

const recentPageNames = ref<string[]>(getRecentPageNames());

function trackRecentPage(pageName: string) {
	const recent = recentPageNames.value.filter((n) => n !== pageName);
	recent.unshift(pageName);
	recentPageNames.value = recent.slice(0, 5);
	localStorage.setItem(RECENT_PAGES_KEY, JSON.stringify(recentPageNames.value));
}

function navigateToPage(pageName: string) {
	trackRecentPage(pageName);
	const isOnBuilder = router.currentRoute.value.name === "builder";
	router.push({ name: "builder", params: { pageId: pageName } });
	if (isOnBuilder) {
		pageStore.setPage(pageName);
	}
}

function makePageCommand(page: BuilderPage): Command {
	return {
		name: `page-${page.name}`,
		title: page.page_title || page.page_name || page.name,
		description: page.route || "/",
		icon: "lucide-file",
		group: "Navigate",
		action: () => navigateToPage(page.name),
	};
}

const recentPages = computed<Command[]>(() => {
	const allPages: BuilderPage[] = searchablePages.data || [];
	return recentPageNames.value
		.map((name) => allPages.find((p) => p.name === name))
		.filter(Boolean)
		.map((page) => makePageCommand(page!));
});

const pageSearchResults = computed<Command[]>(() => {
	const pages: BuilderPage[] = searchablePages.data || [];
	return pages
		.sort((a, b) => {
			const ai = recentPageNames.value.indexOf(a.name);
			const bi = recentPageNames.value.indexOf(b.name);
			return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
		})
		.map(makePageCommand);
});

function runPageQuery() {
	if (activeStep.value?.id !== "search-page") return;
	const q = searchQuery.value.trim();
	if (q) {
		searchablePages.update({
			filters: { is_template: 0 },
			orFilters: {
				page_title: ["like", `%${q}%`],
				page_name: ["like", `%${q}%`],
				route: ["like", `%${q}%`],
			},
			orderBy: "modified desc",
		});
		searchablePages.fetch();
	} else if (recentPageNames.value.length) {
		searchablePages.update({
			filters: { is_template: 0, name: ["in", recentPageNames.value] },
			orFilters: {},
			orderBy: "modified desc",
		});
		searchablePages.fetch();
	}
}

watch(() => activeStep.value?.id, runPageQuery);
watchDebounced(searchQuery, runPageQuery, { debounce: 250 });

const isSearching = computed(
	() => activeStep.value?.id === "search-page" && !!searchQuery.value.trim() && searchablePages.list.loading,
);

// Reset sub-step when the palette closes so it always reopens at root.
watch(show, (val) => {
	if (!val) {
		setTimeout(() => {
			activeStep.value = null;
		}, 150);
	}
});

const commandGroups = computed(() => {
	const q = searchQuery.value.toLowerCase().trim();

	if (activeStep.value?.id === "settings") {
		const items = q
			? settingsCommands.value.filter(
					(s) => s.title.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q),
				)
			: settingsCommands.value;
		const pageItems = items.filter((s) => (s as SettingsCommand).section === "page");
		const globalItems = items.filter((s) => (s as SettingsCommand).section === "global");
		const groups = [];
		if (pageItems.length) {
			groups.push({ title: "Page", hideTitle: false, component: CommandPaletteItem, items: pageItems });
		}
		if (globalItems.length) {
			groups.push({ title: "Global", hideTitle: false, component: CommandPaletteItem, items: globalItems });
		}
		return groups;
	}

	// ── Search-page step ───────────────────────────────────────
	if (activeStep.value?.id === "search-page") {
		if (q) {
			return pageSearchResults.value.length
				? [
						{
							title: "Pages",
							hideTitle: true,
							showDescription: true,
							component: CommandPaletteItem,
							items: pageSearchResults.value,
						},
					]
				: [];
		}
		return recentPages.value.length
			? [
					{
						title: "Recent",
						hideTitle: false,
						showDescription: true,
						component: CommandPaletteItem,
						items: recentPages.value,
					},
				]
			: [];
	}

	// ── Root mode with query ───────────────────────────────────
	if (q) {
		const matchedCommands = staticCommands.value
			.filter((cmd) => cmd.title.toLowerCase().includes(q) || cmd.description?.toLowerCase().includes(q))
			.sort((a, b) => {
				const ai = recentCommandNames.value.indexOf(a.name);
				const bi = recentCommandNames.value.indexOf(b.name);
				return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
			});
		const matchedSettings = settingsCommands.value
			.filter((s) => s.title.toLowerCase().includes(q) || "settings".includes(q))
			.sort((a, b) => {
				const ai = recentCommandNames.value.indexOf(a.name);
				const bi = recentCommandNames.value.indexOf(b.name);
				return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
			});
		const groups = [];
		if (matchedCommands.length) {
			groups.push({
				title: "Commands",
				hideTitle: matchedSettings.length === 0,
				showDescription: true,
				component: CommandPaletteItem,
				items: matchedCommands,
			});
		}
		if (matchedSettings.length) {
			groups.push({
				title: "Settings",
				hideTitle: matchedCommands.length === 0,
				component: CommandPaletteItem,
				items: matchedSettings,
			});
		}
		return groups;
	}

	const groupDefs: { key: string; title: string }[] = [
		{ key: "Navigate", title: "Navigate" },
		{ key: "Page", title: "Page" },
		{ key: "Layers", title: "Layers" },
		{ key: "View", title: "View" },
		{ key: "General", title: "General" },
	];
	const grouped = groupDefs
		.map(({ key, title }) => ({
			title,
			hideTitle: false,
			component: CommandPaletteItem,
			items: staticCommands.value.filter((cmd) => cmd.group === key),
		}))
		.filter((g) => g.items.length > 0);
	if (recentCommands.value.length) {
		return [
			{
				title: "Recent",
				hideTitle: false,
				showDescription: true,
				component: CommandPaletteItem,
				items: recentCommands.value,
			},
			...grouped,
		];
	}
	return grouped;
});

function executeCommand(item: CPItem) {
	if (!String(item.name).startsWith("page-")) {
		trackRecentCommand(item.name as string);
	}
	(item as Command).action?.();
}

function handleBack() {
	activeStep.value = null;
	searchQuery.value = "";
}

defineExpose({ show });
</script>
