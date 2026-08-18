import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import blockController from "@/utils/blockController";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import { useDark, useStorage, useToggle } from "@vueuse/core";
import { nextTick, type Ref } from "vue";
import { __ } from "@/translation";

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

/** raw group keys are matched by the palette; these literals keep the headings extractable */
export const commandGroupLabels: Record<string, string> = {
	Navigate: __("Navigate"),
	Page: __("Page"),
	Layers: __("Layers"),
	View: __("View"),
	General: __("General"),
	Edit: __("Edit"),
};

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
			group: commandGroupLabels[command.group] ?? __(command.group),
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

// the route chunk imports this after pinia is installed, so the lookups resolve
const builderStore = useBuilderStore();
const pageStore = usePageStore();
const canvasStore = useCanvasStore();

const setLayersTab = async () => {
	builderStore.showLeftPanel = true;
	builderStore.leftPanelActiveTab = "Layers";
	await nextTick();
};

commands.register({
	name: "go-to-dashboard",
	title: __("Go to Dashboard"),
	icon: "lucide-layout-dashboard",
	description: __("Navigate"),
	group: "Navigate",
	condition: isBuilderRoute,
	action: () => router.push({ name: "home" }),
});

commands.register({
	name: "preview",
	title: __("Preview Page"),
	icon: "lucide-play",
	description: __("Page"),
	group: "Page",
	condition: isBuilderRoute,
	keys: { key: "p", ctrl: true, description: __("Preview") },
	action: () => {
		pageStore.savePage();
		router.push({ name: "preview", params: { pageId: pageStore.selectedPage as string } });
	},
});

commands.register({
	name: "publish",
	title: __("Publish Page"),
	icon: "lucide-globe",
	description: __("Page"),
	group: "Page",
	condition: isBuilderRoute,
	action: () => pageStore.publishPage(),
});

commands.register({
	name: "duplicate-page",
	title: __("Duplicate Page"),
	icon: "lucide-copy-plus",
	description: __("Page"),
	group: "Page",
	condition: isBuilderRoute,
	action: () => {
		if (pageStore.activePage) {
			pageStore.duplicatePage(pageStore.activePage);
		}
	},
});

commands.register({
	name: "expand-layers",
	title: __("Expand All Layers"),
	icon: "lucide-chevrons-up-down",
	description: __("Layers"),
	group: "Layers",
	condition: isBuilderRoute,
	action: async () => {
		await setLayersTab();
		builderStore.activeLayers?.expandAll();
	},
});

commands.register({
	name: "collapse-layers",
	title: __("Collapse All Layers"),
	icon: "lucide-chevrons-down-up",
	description: __("Layers"),
	group: "Layers",
	condition: isBuilderRoute,
	action: async () => {
		await setLayersTab();
		builderStore.activeLayers?.collapseAll();
	},
});

commands.register({
	name: "toggle-left-panel",
	title: () => (builderStore.showLeftPanel ? __("Hide Left Panel") : __("Show Left Panel")),
	icon: () => (builderStore.showLeftPanel ? "lucide-panel-left-close" : "lucide-panel-left-open"),
	description: __("View"),
	group: "View",
	condition: isBuilderRoute,
	keys: { key: "\\", ctrl: true, shift: true, description: __("Toggle left panel") },
	action: () => (builderStore.showLeftPanel = !builderStore.showLeftPanel),
});

commands.register({
	name: "toggle-right-panel",
	title: () => (builderStore.showRightPanel ? __("Hide Right Panel") : __("Show Right Panel")),
	icon: () => (builderStore.showRightPanel ? "lucide-panel-right-close" : "lucide-panel-right-open"),
	description: __("View"),
	group: "View",
	condition: isBuilderRoute,
	action: () => (builderStore.showRightPanel = !builderStore.showRightPanel),
});

commands.register({
	name: "toggle-theme",
	title: () => (isDark.value ? __("Switch to Light Mode") : __("Switch to Dark Mode")),
	icon: () => (isDark.value ? "lucide-sun" : "lucide-moon"),
	description: __("View"),
	group: "View",
	action: transitionTheme,
});

commands.register({
	name: "shortcuts",
	title: __("Keyboard Shortcuts"),
	icon: "lucide-command",
	description: __("General"),
	group: "General",
	condition: isBuilderRoute,
	keys: { key: "?", description: __("Show keyboard shortcuts") },
	action: () => (builderStore.shortcutsModalOpen = true),
});

// key bindings with no palette entry, so the palette shows what it always did

commands.register({
	name: "toggle-panels",
	title: __("Toggle Panels"),
	icon: "lucide-panels-left-bottom",
	group: "View",
	inPalette: false,
	keys: { key: "\\", ctrl: true, description: __("Toggle panels") },
	action: () => {
		builderStore.showRightPanel = !builderStore.showRightPanel;
		builderStore.showLeftPanel = builderStore.showRightPanel;
	},
});

commands.register({
	name: "toggle-canvas-dark-mode",
	title: __("Toggle Canvas Dark Mode"),
	icon: "lucide-moon",
	group: "View",
	inPalette: false,
	keys: { key: "d", ctrl: true, shift: true, description: __("Toggle canvas dark mode") },
	action: () => (builderStore.canvasDarkMode = !builderStore.canvasDarkMode),
});

commands.register({
	name: "search-blocks",
	title: __("Search Blocks"),
	icon: "lucide-search",
	group: "General",
	inPalette: false,
	keys: { key: "f", ctrl: true, shift: true, description: __("Search blocks") },
	action: () => (builderStore.showSearchBlock = true),
});

commands.register({
	name: "focus-property-search",
	title: __("Focus Property Search"),
	icon: "lucide-search",
	group: "General",
	inPalette: false,
	keys: { key: "f", ctrl: true, allowInInput: true, description: __("Focus property search") },
	action: () => {
		document.querySelector(".properties-search-input")?.querySelector("input")?.focus();
	},
});

commands.register({
	name: "copy-block-styles",
	title: __("Copy Block Styles"),
	icon: "lucide-clipboard-copy",
	group: "Edit",
	inPalette: false,
	keys: { key: "c", ctrl: true, shift: true, description: __("Copy block styles") },
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

commands.register({
	name: "duplicate-block",
	title: __("Duplicate Block"),
	icon: "lucide-copy",
	group: "Edit",
	inPalette: false,
	keys: { key: "d", ctrl: true, description: __("Duplicate block") },
	action: () => {
		if (builderStore.readOnlyMode) return;
		if (!blockController.isBlockSelected() || blockController.multipleBlocksSelected()) return;
		blockController.getSelectedBlocks()[0].duplicateBlock();
	},
});

commands.register({
	name: "undo",
	title: __("Undo"),
	icon: "lucide-undo-2",
	group: "Edit",
	inPalette: false,
	keys: { key: "z", ctrl: true, description: __("Undo") },
	action: () => {
		const canvas = canvasStore.activeCanvas;
		if (canvas?.history?.canUndo) canvas.history.undo();
	},
});

commands.register({
	name: "redo",
	title: __("Redo"),
	icon: "lucide-redo-2",
	group: "Edit",
	inPalette: false,
	keys: { key: "z", ctrl: true, shift: true, description: __("Redo") },
	action: () => {
		const canvas = canvasStore.activeCanvas;
		if (canvas?.history?.canRedo) canvas.history.redo();
	},
});
