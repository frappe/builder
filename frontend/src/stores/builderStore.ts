import BlockContextMenu from "@/components/BlockContextMenu.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderSettings } from "@/types/Builder/BuilderSettings";
import RealTimeHandler from "@/utils/realtimeHandler";
import { useDark, useStorage } from "@vueuse/core";
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
		showRightPanel: <boolean>true,
		showLeftPanel: <boolean>true,
		showHTMLDialog: false,
		showDataScriptDialog: <"block" | "page" | null>null,
		realtime: new RealTimeHandler(),
		readOnlyMode: false,
		viewers: <UserInfo[]>[],
		isFCSite: window.is_fc_site === "True" ? true : false,
		activeFolder: useStorage("activeFolder", ""),
		isDark: useDark({
			attribute: "data-theme",
		}),
	}),
	actions: {
		toggleReadOnlyMode(readonly: boolean | null = null) {
			this.readOnlyMode = readonly ?? !this.readOnlyMode;
		},
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
