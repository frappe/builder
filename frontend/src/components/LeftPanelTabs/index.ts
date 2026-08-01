import LayersIcon from "@/components/Icons/Layers.vue";
import AssetsTab from "@/components/LeftPanelTabs/AssetsTab.vue";
import BlocksTab from "@/components/LeftPanelTabs/BlocksTab.vue";
import CodeTab from "@/components/LeftPanelTabs/CodeTab.vue";
import LayersTab from "@/components/LeftPanelTabs/LayersTab.vue";
import useBuilderStore from "@/stores/builderStore";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component } from "vue";

export type LeftPanelTab = RegistryItem & {
	label: string;
	icon: string | Component;
	component?: Component;
	props?: () => Record<string, unknown>;
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
export const registerLeftPanelTab = leftPanelTabs.register;

/** Call from a component setup. The store lookup below needs an active pinia. */
export function registerBuiltInLeftPanelTabs() {
	const builderStore = useBuilderStore();

	registerLeftPanelTab({
		name: "Blocks",
		label: "Insert",
		icon: "lucide-plus",
		rank: 10,
		component: BlocksTab,
	});

	registerLeftPanelTab({
		name: "Layers",
		label: "Layers",
		icon: LayersIcon,
		rank: 20,
		component: LayersTab,
	});

	registerLeftPanelTab({
		name: "Assets",
		label: "Components",
		icon: "lucide-box",
		rank: 30,
		component: AssetsTab,
	});

	registerLeftPanelTab({
		name: "Code",
		label: "Code",
		icon: "lucide-code",
		rank: 40,
		component: CodeTab,
		// PageScript mounts a CodeMirror instance, so defer it until first open
		lazy: true,
		// a data script dialog needs PageScript mounted even if the tab never opens
		preload: () => builderStore.showDataScriptDialog !== null,
	});

	// not a tab. It toggles a modal, so it declares an action and its own active state
	registerLeftPanelTab({
		name: "variables",
		label: "Variables",
		icon: "lucide-aperture",
		rank: 50,
		action: () => (builderStore.showVariableManager = !builderStore.showVariableManager),
		isActive: () => builderStore.showVariableManager,
	});
}
