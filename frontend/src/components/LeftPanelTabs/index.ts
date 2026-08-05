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

/** Call from a component setup. The store lookup below needs an active pinia. */
export function registerLeftPanelTabs() {
	const builderStore = useBuilderStore();

	leftPanelTabs.register({
		name: "Blocks",
		label: "Insert",
		icon: "lucide-plus",
		component: BlocksTab,
	});

	leftPanelTabs.register({
		name: "Layers",
		label: "Layers",
		icon: LayersIcon,
		component: LayersTab,
	});

	leftPanelTabs.register({
		name: "Assets",
		label: "Components",
		icon: "lucide-box",
		component: AssetsTab,
	});

	leftPanelTabs.register({
		name: "Code",
		label: "Code",
		icon: "lucide-code",
		component: CodeTab,
		// PageScript mounts a CodeMirror instance, so defer it until first open
		lazy: true,
		// a data script dialog needs PageScript mounted even if the tab never opens
		preload: () => builderStore.showDataScriptDialog !== null,
	});

	// not a tab. It toggles a modal, so it declares an action and its own active state
	leftPanelTabs.register({
		name: "tokens",
		label: "Design Tokens",
		icon: "lucide-aperture",
		action: () => (builderStore.showTokenManager = !builderStore.showTokenManager),
		isActive: () => builderStore.showTokenManager,
	});
}
