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
import { __ } from "@/translation";
import { commandGroupLabels, commands, resolveText } from "@/components/Commands";
import { settingsItems } from "@/components/Settings";
import { searchablePages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { watchDebounced } from "@vueuse/core";
import { useShortcut } from "frappe-ui";
import { computed, ref, watch } from "vue";
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

const isBuilderRoute = computed(() => route.name === "builder");

useShortcut({
	key: "k",
	ctrl: true,
	description: __("Open Command Palette"),
	group: __("General"),
	allowInInput: true,
	handler: () => {
		show.value = true;
	},
});

// the two step commands stay here: they drive activeStep, which is local
const openStep = (step: { id: string; label: string; placeholder: string; hint: string }) => {
	activeStep.value = step;
	searchQuery.value = "";
};

commands.register({
	name: "search-page",
	title: __("Search Page"),
	icon: "lucide-file-search",
	description: __("Navigate"),
	group: "Navigate",
	before: "go-to-dashboard",
	keepOpen: true,
	action: () =>
		openStep({
			id: "search-page",
			label: __("Search Page"),
			placeholder: __("Search by name or route..."),
			hint: __("Start typing to search pages"),
		}),
});

commands.register({
	name: "settings",
	title: __("Settings"),
	icon: "lucide-settings-2",
	description: __("General"),
	group: "General",
	after: "shortcuts",
	keepOpen: true,
	action: () =>
		openStep({
			id: "settings",
			label: __("Settings"),
			placeholder: __("Search settings..."),
			hint: __("Browse all settings"),
		}),
});

type PaletteItem = CPItem & { action?: () => void; group?: string; section?: string };

const toPaletteItem = (command: (typeof commands.visible.value)[number]): PaletteItem => ({
	name: command.name,
	title: resolveText(command.title),
	icon: resolveText(command.icon),
	description: command.description,
	group: command.group,
	keepOpen: command.keepOpen,
	action: command.action,
});

const paletteCommands = computed<PaletteItem[]>(() =>
	commands.visible.value.filter((command) => command.inPalette !== false).map(toPaletteItem),
);

function openSettings(tab: string) {
	builderStore.settingsActiveTab = tab;
	builderStore.showSettingsDialog = true;
}

// read from the same registry the settings dialog renders, so a pane registered
// by an extension shows up here too
const settingsCommands = computed<PaletteItem[]>(() =>
	settingsItems.visible.value
		.filter((item) => !item.disabled)
		.filter((item) => isBuilderRoute.value || item.group === "Global")
		.map((item) => ({
			name: item.name,
			title: item.title,
			description: __("Settings"),
			icon: item.icon,
			section: item.group === "Current Page" ? "page" : "global",
			action: () => openSettings(item.name),
		})),
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

const recentCommands = computed<PaletteItem[]>(() => {
	const all = [...paletteCommands.value, ...settingsCommands.value];
	return recentCommandNames.value
		.map((name) => all.find((c) => c.name === name))
		.filter(Boolean) as PaletteItem[];
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

function makePageCommand(page: BuilderPage): PaletteItem {
	return {
		name: `page-${page.name}`,
		title: page.page_title || page.page_name || page.name,
		description: page.route || "/",
		icon: "lucide-file",
		group: "Navigate",
		action: () => navigateToPage(page.name),
	};
}

const recentPages = computed<PaletteItem[]>(() => {
	const allPages: BuilderPage[] = searchablePages.data || [];
	return recentPageNames.value
		.map((name) => allPages.find((p) => p.name === name))
		.filter(Boolean)
		.map((page) => makePageCommand(page!));
});

const pageSearchResults = computed<PaletteItem[]>(() => {
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
		});
		searchablePages.fetch();
	} else if (recentPageNames.value.length) {
		searchablePages.update({
			filters: { is_template: 0, name: ["in", recentPageNames.value] },
			orFilters: {},
		});
		searchablePages.fetch();
	}
}

watch(() => activeStep.value?.id, runPageQuery);
watchDebounced(searchQuery, runPageQuery, { debounce: 250 });

const isSearching = computed(
	() => activeStep.value?.id === "search-page" && !!searchQuery.value.trim() && searchablePages.list.loading,
);

const byRecency = (a: PaletteItem, b: PaletteItem) => {
	const ai = recentCommandNames.value.indexOf(a.name as string);
	const bi = recentCommandNames.value.indexOf(b.name as string);
	return (ai === -1 ? Infinity : ai) - (bi === -1 ? Infinity : bi);
};

const commandGroups = computed(() => {
	const q = searchQuery.value.toLowerCase().trim();

	if (activeStep.value?.id === "settings") {
		const items = q
			? settingsCommands.value.filter(
					(s) => s.title.toLowerCase().includes(q) || s.description?.toLowerCase().includes(q),
				)
			: settingsCommands.value;
		const pageItems = items.filter((s) => s.section === "page");
		const globalItems = items.filter((s) => s.section === "global");
		const groups = [];
		if (pageItems.length) {
			groups.push({ title: __("Page"), hideTitle: false, component: CommandPaletteItem, items: pageItems });
		}
		if (globalItems.length) {
			groups.push({
				title: __("Global"),
				hideTitle: false,
				component: CommandPaletteItem,
				items: globalItems,
			});
		}
		return groups;
	}

	// ── Search-page step ───────────────────────────────────────
	if (activeStep.value?.id === "search-page") {
		if (q) {
			return pageSearchResults.value.length
				? [
						{
							title: __("Pages"),
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
						title: __("Recent"),
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
		const matchedCommands = paletteCommands.value
			.filter((cmd) => cmd.title.toLowerCase().includes(q) || cmd.description?.toLowerCase().includes(q))
			.sort(byRecency);
		const matchedSettings = settingsCommands.value
			.filter((s) => s.title.toLowerCase().includes(q) || "settings".includes(q))
			.sort(byRecency);
		const groups = [];
		if (matchedCommands.length) {
			groups.push({
				title: __("Commands"),
				hideTitle: matchedSettings.length === 0,
				showDescription: true,
				component: CommandPaletteItem,
				items: matchedCommands,
			});
		}
		if (matchedSettings.length) {
			groups.push({
				title: __("Settings"),
				hideTitle: matchedCommands.length === 0,
				component: CommandPaletteItem,
				items: matchedSettings,
			});
		}
		return groups;
	}

	const groupDefs = ["Navigate", "Page", "Layers", "View", "General"];
	const grouped = groupDefs
		.map((group) => ({
			title: commandGroupLabels[group] ?? __(group),
			hideTitle: false,
			component: CommandPaletteItem,
			items: paletteCommands.value.filter((cmd) => cmd.group === group),
		}))
		.filter((g) => g.items.length > 0);
	if (recentCommands.value.length) {
		return [
			{
				title: __("Recent"),
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
	(item as PaletteItem).action?.();
}

function handleBack() {
	activeStep.value = null;
	searchQuery.value = "";
}

defineExpose({ show });
</script>
