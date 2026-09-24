import router from "@/router";
import useBuilderStore from "@/stores/builderStore";
import useCanvasStore from "@/stores/canvasStore";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import blockController from "@/utils/blockController";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import { useDark, useStorage, useToggle } from "@vueuse/core";
import type { KeyboardShortcutCombo } from "frappe-ui";
import { nextTick, type Ref } from "vue";

/** A key binding for a command. The description labels it in the shortcuts dialog. */
export type CommandKeys = {
	combo: KeyboardShortcutCombo;
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
 * Every command that declares a binding, shaped for useKeyboardShortcut. Read once at
 * setup, so a command registered later gets no binding until the next reload.
 */
export function commandShortcuts() {
	return commands.all.value
		.filter((command) => command.keys)
		.map((command) => ({
			...command.keys!,
			group: commandGroupLabels[command.group] ?? __(command.group),
			enabled: command.condition,
			handler: () => {
				builderStore.blockContextMenu?.hideContextMenu();
				command.action();
			},
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

// module scope: useStorage in the handler would leak a subscription per keypress
const copiedStyle = useStorage("copiedStyle", { blockId: "", style: {} }, sessionStorage) as Ref<StyleCopy>;

const setLayersTab = async () => {
	builderStore.showLeftPanel = true;
	builderStore.leftPanelActiveTab = "Layers";
	await nextTick();
};

commands.registerBuiltIn({
	name: "go-to-dashboard",
	title: __("Go to Dashboard"),
	icon: "lucide-layout-dashboard",
	description: __("Navigate"),
	group: "Navigate",
	condition: isBuilderRoute,
	action: () => router.push({ name: "home" }),
});

commands.registerBuiltIn({
	name: "preview",
	title: __("Preview Page"),
	icon: "lucide-play",
	group: "General",
	condition: isBuilderRoute,
	keys: { combo: "Mod+P", description: __("Preview Page") },
	action: () => {
		pageStore.savePage();
		router.push({ name: "preview", params: { pageId: pageStore.selectedPage as string } });
	},
});

commands.registerBuiltIn({
	name: "publish",
	title: __("Publish Page"),
	icon: "lucide-globe",
	description: __("Page"),
	group: "Page",
	condition: isBuilderRoute,
	// like the publish button: a staging page stays on staging until Go Live
	action: () => pageStore.publishPage(true, Boolean(pageStore.activePage?.staging)),
});

commands.registerBuiltIn({
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

commands.registerBuiltIn({
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

commands.registerBuiltIn({
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

commands.registerBuiltIn({
	name: "toggle-left-panel",
	title: () => (builderStore.showLeftPanel ? __("Hide Left Panel") : __("Show Left Panel")),
	icon: () => (builderStore.showLeftPanel ? "lucide-panel-left-close" : "lucide-panel-left-open"),
	description: __("View"),
	group: "View",
	condition: isBuilderRoute,
	keys: { combo: "Mod+Shift+Backslash", description: __("Toggle Left Panel") },
	action: () => (builderStore.showLeftPanel = !builderStore.showLeftPanel),
});

commands.registerBuiltIn({
	name: "toggle-right-panel",
	title: () => (builderStore.showRightPanel ? __("Hide Right Panel") : __("Show Right Panel")),
	icon: () => (builderStore.showRightPanel ? "lucide-panel-right-close" : "lucide-panel-right-open"),
	description: __("View"),
	group: "View",
	condition: isBuilderRoute,
	action: () => (builderStore.showRightPanel = !builderStore.showRightPanel),
});

commands.registerBuiltIn({
	name: "toggle-theme",
	title: () => (isDark.value ? __("Switch to Light Mode") : __("Switch to Dark Mode")),
	icon: () => (isDark.value ? "lucide-sun" : "lucide-moon"),
	description: __("View"),
	group: "View",
	action: transitionTheme,
});

commands.registerBuiltIn({
	name: "shortcuts",
	title: __("Keyboard Shortcuts"),
	icon: "lucide-command",
	description: __("General"),
	group: "General",
	condition: isBuilderRoute,
	keys: { combo: "Shift+Slash", description: __("Show Keyboard Shortcuts") },
	action: () => (builderStore.shortcutsModalOpen = true),
});

// key bindings with no palette entry, so the palette shows what it always did

commands.registerBuiltIn({
	name: "toggle-panels",
	title: __("Toggle Panels"),
	icon: "lucide-panels-left-bottom",
	group: "View",
	inPalette: false,
	keys: { combo: "Mod+Backslash", description: __("Toggle Panels") },
	action: () => {
		builderStore.showRightPanel = !builderStore.showRightPanel;
		builderStore.showLeftPanel = builderStore.showRightPanel;
	},
});

commands.registerBuiltIn({
	name: "toggle-canvas-dark-mode",
	title: __("Toggle Canvas Dark Mode"),
	icon: "lucide-moon",
	group: "View",
	inPalette: false,
	keys: { combo: "Mod+Shift+D", description: __("Toggle Canvas Dark Mode") },
	action: () => (builderStore.canvasDarkMode = !builderStore.canvasDarkMode),
});

commands.registerBuiltIn({
	name: "search-blocks",
	title: __("Search Blocks"),
	icon: "lucide-search",
	group: "General",
	inPalette: false,
	keys: { combo: "Mod+Shift+F", description: __("Search Blocks") },
	action: () => (builderStore.showSearchBlock = true),
});

commands.registerBuiltIn({
	name: "focus-property-search",
	title: __("Focus Property Search"),
	icon: "lucide-search",
	group: "General",
	inPalette: false,
	keys: { combo: "Mod+F", allowInInput: true, description: __("Focus Property Search") },
	action: () => {
		document.querySelector(".properties-search-input")?.querySelector("input")?.focus();
	},
});

commands.registerBuiltIn({
	name: "copy-block-styles",
	title: __("Copy Block Styles"),
	icon: "lucide-clipboard-copy",
	group: "Edit",
	inPalette: false,
	keys: { combo: "Mod+Shift+C", description: __("Copy Block Styles") },
	action: () => {
		if (!blockController.isBlockSelected() || blockController.multipleBlocksSelected()) return;
		const block = blockController.getSelectedBlocks()[0];
		copiedStyle.value = { blockId: block.blockId, style: block.getStylesCopy() };
	},
});

commands.registerBuiltIn({
	name: "duplicate-block",
	title: __("Duplicate Block"),
	icon: "lucide-copy",
	group: "Edit",
	inPalette: false,
	keys: { combo: "Mod+D", description: __("Duplicate Block") },
	action: () => {
		if (builderStore.readOnlyMode) return;
		if (!blockController.isBlockSelected() || blockController.multipleBlocksSelected()) return;
		blockController.getSelectedBlocks()[0].duplicateBlock();
	},
});

commands.registerBuiltIn({
	name: "undo",
	title: __("Undo"),
	icon: "lucide-undo-2",
	group: "Edit",
	inPalette: false,
	keys: { combo: "Mod+Z", description: __("Undo") },
	action: () => {
		const canvas = canvasStore.activeCanvas;
		if (canvas?.history?.canUndo) canvas.history.undo();
	},
});

commands.registerBuiltIn({
	name: "redo",
	title: __("Redo"),
	icon: "lucide-redo-2",
	group: "Edit",
	inPalette: false,
	keys: { combo: "Mod+Shift+Z", description: __("Redo") },
	action: () => {
		const canvas = canvasStore.activeCanvas;
		if (canvas?.history?.canRedo) canvas.history.redo();
	},
});
