import router from "@/router";
import useAIStore from "@/stores/aiStore";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import { useDark, useStorage, useToggle } from "@vueuse/core";
import { nextTick, type Ref } from "vue";

/** A key binding for a command. The description labels it in the shortcuts modal. */
export type CommandKeys = {
	key: string;
	ctrl?: boolean;
	shift?: boolean;
	alt?: boolean;
	allowInInput?: boolean;
	preventDefault?: boolean;
	description: string;
};

export type Command = RegistryItem & {
	/** a function when the label depends on state, such as Show or Hide Left Panel */
	title: string | (() => string);
	icon: string | (() => string);
	description?: string;
	group: string;
	action: () => void;
	keys?: CommandKeys;
	/** keep the palette open, for a command that opens a step */
	keepOpen?: boolean;
	/** false for a key binding that should not be listed in the palette */
	inPalette?: boolean;
};

export const commands = createRegistry<Command>();
export const registerCommand = commands.register;

export const resolveText = (value: string | (() => string)) =>
	typeof value === "function" ? value() : value;

export function runCommand(name: string) {
	commands.all.value.find((command) => command.name === name)?.action();
}

/**
 * Every command that declares a binding, shaped for useShortcut. Read once at
 * setup, so a command registered later gets no binding until the next reload.
 */
export function commandShortcuts() {
	return commands.all.value
		.filter((command) => command.keys)
		.map((command) => ({
			...command.keys!,
			group: command.group,
			condition: command.condition,
			handler: command.action,
		}));
}

const isBuilderRoute = () => router.currentRoute.value.name === "builder";

const isDark = useDark({ attribute: "data-theme" });
const toggleDark = useToggle(isDark);

const transitionTheme = () => {
	if (document.startViewTransition && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
		document.startViewTransition(() => toggleDark());
	} else {
		toggleDark();
	}
};

/** Call from a component setup. The store lookups below need an active pinia. */
export function registerBuiltInCommands() {
	const builderStore = useBuilderStore();
	const pageStore = usePageStore();
	const canvasStore = useCanvasStore();
	const aiStore = useAIStore();

	const setLayersTab = async () => {
		builderStore.showLeftPanel = true;
		builderStore.leftPanelActiveTab = "Layers";
		await nextTick();
	};

	registerCommand({
		name: "go-to-dashboard",
		title: "Go to Dashboard",
		icon: "lucide-layout-dashboard",
		description: "Navigate",
		group: "Navigate",
		rank: 10,
		condition: isBuilderRoute,
		action: () => router.push({ name: "home" }),
	});

	registerCommand({
		name: "preview",
		title: "Preview Page",
		icon: "lucide-play",
		description: "Page",
		group: "Page",
		rank: 20,
		condition: isBuilderRoute,
		keys: { key: "p", ctrl: true, description: "Preview" },
		action: () => {
			pageStore.savePage();
			router.push({ name: "preview", params: { pageId: pageStore.selectedPage as string } });
		},
	});

	registerCommand({
		name: "publish",
		title: "Publish Page",
		icon: "lucide-globe",
		description: "Page",
		group: "Page",
		rank: 30,
		condition: isBuilderRoute,
		action: () => pageStore.publishPage(),
	});

	registerCommand({
		name: "duplicate-page",
		title: "Duplicate Page",
		icon: "lucide-copy-plus",
		description: "Page",
		group: "Page",
		rank: 40,
		condition: isBuilderRoute,
		action: () => {
			if (pageStore.activePage) {
				pageStore.duplicatePage(pageStore.activePage);
			}
		},
	});

	registerCommand({
		name: "expand-layers",
		title: "Expand All Layers",
		icon: "lucide-chevrons-up-down",
		description: "Layers",
		group: "Layers",
		rank: 50,
		condition: isBuilderRoute,
		action: async () => {
			await setLayersTab();
			builderStore.activeLayers?.expandAll();
		},
	});

	registerCommand({
		name: "collapse-layers",
		title: "Collapse All Layers",
		icon: "lucide-chevrons-down-up",
		description: "Layers",
		group: "Layers",
		rank: 60,
		condition: isBuilderRoute,
		action: async () => {
			await setLayersTab();
			builderStore.activeLayers?.collapseAll();
		},
	});

	registerCommand({
		name: "toggle-left-panel",
		title: () => `${builderStore.showLeftPanel ? "Hide" : "Show"} Left Panel`,
		icon: () => (builderStore.showLeftPanel ? "lucide-panel-left-close" : "lucide-panel-left-open"),
		description: "View",
		group: "View",
		rank: 70,
		condition: isBuilderRoute,
		keys: { key: "\\", ctrl: true, shift: true, description: "Toggle left panel" },
		action: () => (builderStore.showLeftPanel = !builderStore.showLeftPanel),
	});

	registerCommand({
		name: "toggle-right-panel",
		title: () => `${builderStore.showRightPanel ? "Hide" : "Show"} Right Panel`,
		icon: () => (builderStore.showRightPanel ? "lucide-panel-right-close" : "lucide-panel-right-open"),
		description: "View",
		group: "View",
		rank: 80,
		condition: isBuilderRoute,
		action: () => (builderStore.showRightPanel = !builderStore.showRightPanel),
	});

	registerCommand({
		name: "toggle-theme",
		title: () => `Switch to ${isDark.value ? "Light" : "Dark"} Mode`,
		icon: () => (isDark.value ? "lucide-sun" : "lucide-moon"),
		description: "View",
		group: "View",
		rank: 90,
		action: transitionTheme,
	});

	registerCommand({
		name: "shortcuts",
		title: "Keyboard Shortcuts",
		icon: "lucide-command",
		description: "General",
		group: "General",
		rank: 100,
		condition: isBuilderRoute,
		keys: { key: "?", description: "Show keyboard shortcuts" },
		action: () => (builderStore.shortcutsModalOpen = true),
	});

	// key bindings with no palette entry, so the palette shows what it always did

	registerCommand({
		name: "toggle-panels",
		title: "Toggle Panels",
		icon: "lucide-panels-left-bottom",
		group: "View",
		rank: 110,
		inPalette: false,
		keys: { key: "\\", ctrl: true, description: "Toggle panels" },
		action: () => {
			builderStore.showRightPanel = !builderStore.showRightPanel;
			builderStore.showLeftPanel = builderStore.showRightPanel;
		},
	});

	registerCommand({
		name: "toggle-canvas-dark-mode",
		title: "Toggle Canvas Dark Mode",
		icon: "lucide-moon",
		group: "View",
		rank: 120,
		inPalette: false,
		keys: { key: "d", ctrl: true, shift: true, description: "Toggle canvas dark mode" },
		action: () => (builderStore.canvasDarkMode = !builderStore.canvasDarkMode),
	});

	registerCommand({
		name: "search-blocks",
		title: "Search Blocks",
		icon: "lucide-search",
		group: "General",
		rank: 130,
		inPalette: false,
		keys: { key: "f", ctrl: true, shift: true, description: "Search blocks" },
		action: () => (builderStore.showSearchBlock = true),
	});

	registerCommand({
		name: "focus-property-search",
		title: "Focus Property Search",
		icon: "lucide-search",
		group: "General",
		rank: 140,
		inPalette: false,
		keys: { key: "f", ctrl: true, allowInInput: true, description: "Focus property search" },
		action: () => {
			document.querySelector(".properties-search-input")?.querySelector("input")?.focus();
		},
	});

	registerCommand({
		name: "copy-block-styles",
		title: "Copy Block Styles",
		icon: "lucide-clipboard-copy",
		group: "Edit",
		rank: 150,
		inPalette: false,
		keys: { key: "c", ctrl: true, shift: true, description: "Copy block styles" },
		action: () => {
			if (!blockController.isBlockSelected() || blockController.multipleBlocksSelected()) return;
			const block = blockController.getSelectedBlocks()[0];
			const copiedStyle = useStorage(
				"copiedStyle",
				{ blockId: "", style: {} },
				sessionStorage,
			) as Ref<StyleCopy>;
			copiedStyle.value = { blockId: block.blockId, style: block.getStylesCopy() };
		},
	});

	registerCommand({
		name: "duplicate-block",
		title: "Duplicate Block",
		icon: "lucide-copy",
		group: "Edit",
		rank: 160,
		inPalette: false,
		keys: { key: "d", ctrl: true, description: "Duplicate block" },
		action: () => {
			if (builderStore.readOnlyMode) return;
			if (!blockController.isBlockSelected() || blockController.multipleBlocksSelected()) return;
			blockController.getSelectedBlocks()[0].duplicateBlock();
		},
	});

	registerCommand({
		name: "edit-with-ai",
		title: "Edit Block with AI",
		icon: "lucide-sparkles",
		group: "Edit",
		rank: 170,
		inPalette: false,
		keys: { key: "i", ctrl: true, description: "Edit block with AI" },
		condition: () =>
			builderStore.isAIEnabled &&
			!blockController.isRoot() &&
			!blockController.multipleBlocksSelected() &&
			!builderStore.readOnlyMode,
		action: () => {
			const block = blockController.getSelectedBlocks()[0];
			if (block) {
				aiStore.editWithAI(block);
			}
		},
	});

	registerCommand({
		name: "undo",
		title: "Undo",
		icon: "lucide-undo-2",
		group: "Edit",
		rank: 175,
		inPalette: false,
		keys: { key: "z", ctrl: true, description: "Undo" },
		action: () => {
			const canvas = canvasStore.activeCanvas;
			if (canvas?.history?.canUndo) canvas.history.undo();
		},
	});

	registerCommand({
		name: "redo",
		title: "Redo",
		icon: "lucide-redo-2",
		group: "Edit",
		rank: 176,
		inPalette: false,
		keys: { key: "z", ctrl: true, shift: true, description: "Redo" },
		action: () => {
			const canvas = canvasStore.activeCanvas;
			if (canvas?.history?.canRedo) canvas.history.redo();
		},
	});

	registerCommand({
		name: "delete-page",
		title: "Delete Page",
		icon: "lucide-trash-2",
		group: "General",
		rank: 180,
		inPalette: false,
		// same binding as toggle-canvas-dark-mode, as it was before this registry
		keys: { key: "d", ctrl: true, shift: true, description: "Delete Page" },
		condition: () => Boolean(pageStore.activePage && !pageStore.activePage.is_standard),
		action: () => {
			if (pageStore.activePage && !pageStore.activePage.is_standard) {
				pageStore.deletePage(pageStore.activePage).then(() => router.push({ name: "home" }));
			}
		},
	});
}
