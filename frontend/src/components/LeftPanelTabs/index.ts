import BuilderAIChatPanel from "@/components/BuilderAIChatPanel.vue";
import LayersIcon from "@/components/Icons/Layers.vue";
import AssetsTab from "@/components/LeftPanelTabs/AssetsTab.vue";
import BlocksTab from "@/components/LeftPanelTabs/BlocksTab.vue";
import CodeTab from "@/components/LeftPanelTabs/CodeTab.vue";
import LayersTab from "@/components/LeftPanelTabs/LayersTab.vue";
import useBuilderStore from "@/stores/builderStore";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component } from "vue";
import { __ } from "@/translation";

export type LeftPanelTab = RegistryItem & {
	label: string;
	icon: string | Component;
	component?: Component;
	props?: () => Record<string, unknown>;
	/** binding that opens the tab; the panel labels the button with it */
	shortcut?: { key: string; ctrl?: boolean; shift?: boolean };
	/** mount on first open, then keep alive */
	lazy?: boolean;
	/** mount a lazy tab early, before the user opens it */
	preload?: () => boolean;
	/** clicking runs this instead of switching tab */
	action?: () => void;
	/** for action tabs that own their own active state */
	isActive?: () => boolean;
};

export const leftPanelTabs = createRegistry<LeftPanelTab>();

// the route chunk imports this after pinia is installed, so the lookup resolves
const builderStore = useBuilderStore();

leftPanelTabs.register({
	name: "Blocks",
	label: __("Insert"),
	icon: "lucide-plus",
	component: BlocksTab,
	shortcut: { key: "i", ctrl: true, shift: true },
});

leftPanelTabs.register({
	name: "Layers",
	label: __("Layers"),
	icon: LayersIcon,
	component: LayersTab,
	shortcut: { key: "l", ctrl: true, shift: true },
});

leftPanelTabs.register({
	name: "Assets",
	label: __("Components"),
	icon: "lucide-box",
	component: AssetsTab,
	shortcut: { key: "a", ctrl: true, shift: true },
});

leftPanelTabs.register({
	name: "Code",
	label: __("Code"),
	icon: "lucide-code",
	component: CodeTab,
	shortcut: { key: "k", ctrl: true, shift: true },
	// PageScript mounts a CodeMirror instance, so defer it until first open
	lazy: true,
	// a data script dialog needs PageScript mounted even if the tab never opens,
	// and so does a script the chat asks to open: the watchers that open the
	// editor live INSIDE PageScript, so until something mounts it the flag is
	// set for nobody to read
	preload: () =>
		builderStore.showDataScriptDialog !== null || builderStore.openClientScript !== null,
});

// not a tab. It toggles a modal, so it declares an action and its own active state
leftPanelTabs.register({
	name: "tokens",
	label: __("Design Tokens"),
	icon: "lucide-aperture",
	shortcut: { key: "v", ctrl: true, shift: true },
	action: () => (builderStore.showTokenManager = !builderStore.showTokenManager),
	isActive: () => builderStore.showTokenManager,
});

leftPanelTabs.register({
	name: "Chat",
	label: __("Bob AI"),
	icon: "lucide-sparkle",
	component: BuilderAIChatPanel,
	shortcut: { key: "o", ctrl: true, shift: true },
});
