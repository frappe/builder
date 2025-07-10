import BlockContextMenu from "@/components/BlockContextMenu.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderSettings } from "@/types/Builder/BuilderSettings";
import RealTimeHandler from "@/utils/realtimeHandler";
import { useStorage } from "@vueuse/core";
import { defineStore } from "pinia";
import { toast } from "vue-sonner";
import type Dialog from "../components/Controls/Dialog.vue";
import BlockLayers from "./components/BlockLayers.vue";

declare global {
	interface Window {
		is_fc_site?: boolean | string;
	}
}

const useBuilderStore = defineStore("builderStore", {
	state: () => ({
		activeLayers: <InstanceType<typeof BlockLayers> | null>null,
		appDialogs: <(typeof Dialog)[]>[],
		blockContextMenu: <InstanceType<typeof BlockContextMenu> | null>null,
		propertyFilter: <string | null>null,
		mode: <BuilderMode>"select", // check setEvents in BuilderCanvas for usage
		lastMode: <BuilderMode>"select",
		autoSave: true,
		showSearchBlock: false,
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
		showDataScriptDialog: false,
		realtime: new RealTimeHandler(),
		viewers: <UserInfo[]>[],
		isFCSite: window.is_fc_site === "{{ is_fc_site }}" ? false : window.is_fc_site,
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
