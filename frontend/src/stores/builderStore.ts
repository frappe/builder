import type Block from "@/block";
import BlockContextMenu from "@/components/BlockContextMenu.vue";
import type BuilderCanvas from "@/components/BuilderCanvas.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderSettings } from "@/types/Builder/BuilderSettings";
import RealTimeHandler from "@/utils/realtimeHandler";
import { useStorage } from "@vueuse/core";
import { defineStore } from "pinia";
import { toast } from "vue-sonner";
import BlockLayers from "./components/BlockLayers.vue";

const useBuilderStore = defineStore("builderStore", {
	state: () => ({
		activeCanvas: <InstanceType<typeof BuilderCanvas> | null>null,
		activeLayers: <InstanceType<typeof BlockLayers> | null>null,
		blockContextMenu: <InstanceType<typeof BlockContextMenu> | null>null,
		editableBlock: <Block | null>null,
		propertyFilter: <string | null>null,
		mode: <BuilderMode>"select", // check setEvents in BuilderCanvas for usage
		lastMode: <BuilderMode>"select",
		autoSave: true,
		builderLayout: {
			rightPanelWidth: 275,
			leftPanelWidth: 250,
			scriptEditorHeight: 300,
			optionsPanelWidth: 57,
		},
		leftPanelActiveTab: <LeftSidebarTabOption>"Layers",
		rightPanelActiveTab: <RightSidebarTabOption>"Properties",
		showDashboardSidebar: useStorage("showDashboardSidebar", true),
		showRightPanel: <boolean>true,
		showLeftPanel: <boolean>true,
		showHTMLDialog: false,
		realtime: new RealTimeHandler(),
		viewers: <UserInfo[]>[],
		activeFolder: useStorage("activeFolder", ""),
	}),
	actions: {
		setHomePage(route: string) {
			return builderSettings.setValue
				.submit({
					home_page: route,
				})
				.then(() => {
					toast.success("Homepage set successfully");
				});
		},
		unsetHomePage() {
			return builderSettings.setValue
				.submit({
					home_page: "",
				})
				.then(() => {
					toast.success("This page will no longer be the homepage");
				});
		},
		updateBuilderSettings(key: keyof BuilderSettings, value: any) {
			return builderSettings.setValue
				.submit({
					[key]: value,
				})
				.then(() => {
					builderSettings.reload();
				});
		},
		openBuilderSettings() {
			window.open("/app/builder-settings", "_blank");
		},
	},
});

export default useBuilderStore;
