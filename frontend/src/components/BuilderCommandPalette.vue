<template>
	<CommandPalette
		v-model:show="show"
		v-model:searchQuery="searchQuery"
		:groups="commandGroups"
		:step-label="activeStep?.label"
		:placeholder="activeStep?.placeholder"
		:hint="activeStep?.hint"
		@select="executeCommand"
		@back="handleBack" />
</template>

<script setup lang="ts">
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import usePageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/doctypes";
import { useDark, useToggle } from "@vueuse/core";
import { computed, nextTick, ref } from "vue";
import { useRouter } from "vue-router";
import type { CommandPaletteItem as CPItem } from "./CommandPalette.vue";
import CommandPalette from "./CommandPalette.vue";
import CommandPaletteItem from "./CommandPaletteItem.vue";

const show = ref(false);
const searchQuery = ref("");
const activeStep = ref<{ id: string; label: string; placeholder: string; hint: string } | null>(null);

const builderStore = useBuilderStore();
const pageStore = usePageStore();
const router = useRouter();

const isDark = useDark({ attribute: "data-theme" });
const toggleDark = useToggle(isDark);

const transitionTheme = () => {
	if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		document.startViewTransition(() => toggleDark());
	} else {
		toggleDark();
	}
};

interface Command extends CPItem {
	action: () => void;
}

const staticCommands = computed<Command[]>(() => [
	{
		name: "expand-layers",
		title: "Expand All Layers",
		icon: "lucide-chevrons-down-up",
		description: "Layers",
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
		icon: "lucide-chevrons-up-down",
		description: "Layers",
		action: async () => {
			builderStore.showLeftPanel = true;
			builderStore.leftPanelActiveTab = "Layers";
			await nextTick();
			builderStore.activeLayers?.collapseAll();
		},
	},
	{
		name: "toggle-left-panel",
		title: `${builderStore.showLeftPanel ? "Hide" : "Show"} Left Panel`,
		icon: builderStore.showLeftPanel ? "lucide-panel-left-close" : "lucide-panel-left-open",
		description: "View",
		action: () => {
			builderStore.showLeftPanel = !builderStore.showLeftPanel;
		},
	},
	{
		name: "toggle-right-panel",
		title: `${builderStore.showRightPanel ? "Hide" : "Show"} Right Panel`,
		icon: builderStore.showRightPanel ? "lucide-panel-right-close" : "lucide-panel-right-open",
		description: "View",
		action: () => {
			builderStore.showRightPanel = !builderStore.showRightPanel;
		},
	},
	{
		name: "toggle-theme",
		title: `Switch to ${isDark.value ? "Light" : "Dark"} Mode`,
		icon: isDark.value ? "lucide-sun" : "lucide-moon",
		description: "Theme",
		action: () => transitionTheme(),
	},
	{
		name: "preview",
		title: "Preview Page",
		icon: "lucide-play",
		description: "Page",
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
		action: () => {
			pageStore.publishPage();
		},
	},
	{
		name: "add-redirect",
		title: "Manage Redirects",
		icon: "lucide-arrow-right",
		description: "Page",
		action: () => {
			builderStore.settingsActiveTab = "global_redirects";
			builderStore.showSettingsDialog = true;
		},
	},
	{
		name: "analytics",
		title: "View Page Analytics",
		icon: "lucide-bar-chart-2",
		description: "Page",
		action: () => {
			builderStore.settingsActiveTab = "page_analytics";
			builderStore.showSettingsDialog = true;
		},
	},
	{
		name: "search-page",
		title: "Search Page",
		icon: "lucide-file-search",
		description: "Navigate",
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
]);

const filteredStaticCommands = computed(() => {
	const q = searchQuery.value.toLowerCase().trim();
	if (!q) return staticCommands.value;
	return staticCommands.value.filter(
		(cmd) => cmd.title.toLowerCase().includes(q) || cmd.description?.toLowerCase().includes(q),
	);
});

const pageSearchResults = computed<Command[]>(() => {
	const q = searchQuery.value.toLowerCase().trim();
	if (!q) return [];
	const pages: BuilderPage[] = webPages.data || [];
	return pages
		.filter((page) => {
			const title = (page.page_title || page.page_name || "").toLowerCase();
			const route = (page.route || "").toLowerCase();
			return title.includes(q) || route.includes(q);
		})
		.slice(0, 8)
		.map((page) => ({
			name: `page-${page.name}`,
			title: page.page_title || page.page_name || page.name,
			description: page.route || "/",
			icon: "lucide-file",
			action: () => {
				router.push({ name: "builder", params: { pageId: page.name } });
			},
		}));
});

const commandGroups = computed(() => {
	// Search-page step: only show page results
	if (activeStep.value?.id === "search-page") {
		return pageSearchResults.value.length
			? [{ title: "Pages", hideTitle: true, component: CommandPaletteItem, items: pageSearchResults.value }]
			: [];
	}

	// Root: show commands only
	return filteredStaticCommands.value.length
		? [
				{
					title: "Commands",
					hideTitle: true,
					component: CommandPaletteItem,
					items: filteredStaticCommands.value,
				},
			]
		: [];
});

function executeCommand(item: CPItem) {
	(item as Command).action?.();
}

function handleBack() {
	activeStep.value = null;
	searchQuery.value = "";
}

defineExpose({ show });
</script>
