import BlockContextMenu from "@/components/BlockContextMenu.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderSettings } from "@/types/doctypes";
import RealTimeHandler from "@/utils/realtimeHandler";
import { useDark, useStorage } from "@vueuse/core";
import { toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { defineStore } from "pinia";
import BlockLayers from "./components/BlockLayers.vue";

const { capture } = useTelemetry();

declare global {
	interface Window {
		is_fc_site?: boolean | string;
	}
}

const useBuilderStore = defineStore("builderStore", {
	state: () => ({
		activeLayers: <InstanceType<typeof BlockLayers> | null>null,
		blockContextMenu: <InstanceType<typeof BlockContextMenu> | null>null,
		propertyFilter: <string | null>null,
		mode: <BuilderMode>"select", // check setEvents in BuilderCanvas for usage
		lastMode: <BuilderMode>"select",
		autoSave: true,
		showSearchBlock: false,
		builderLayout: {
			rightPanelWidth: 275,
			leftPanelWidth: 300,
			scriptEditorHeight: 300,
			optionsPanelWidth: 57,
		},
		leftPanelActiveTab: <LeftSidebarTabOption>"Layers",
		showRightPanel: <boolean>true,
		showLeftPanel: <boolean>true,
		showVersionHistory: <boolean>false,
		showHTMLDialog: false,
		openClientScript: <string | null>null,
		showDataScriptDialog: <"page" | null>null,
		realtime: new RealTimeHandler(),
		readOnlyMode: false,
		// An AI build is streaming onto the canvas: the server owns the draft, so the
		// editor's autosave must stand down (it would persist the partial preview).
		aiBuildingCanvas: false,
		// Bob's current activity line, mirrored from the chat controller so the
		// canvas build overlay can narrate what's happening ("Designing the hero…").
		aiBuildStatus: <string>"",
		// Bumped once each time a build settles — the overlay watches it to fire a
		// one-shot "done" flourish on the canvas.
		aiBuildDoneTick: 0,
		viewers: <UserInfo[]>[],
		isFCSite: window.is_fc_site === "True" ? true : false,
		activeFolder: useStorage("activeFolder", ""),
		isDark: useDark({
			attribute: "data-theme",
		}),
		canvasDarkMode: useStorage("canvasDarkMode", false),
		highlightBlocksWithClientScripts: false,
		showSettingsDialog: false,
		settingsActiveTab: useStorage("settingsActiveTab", "page_general"),
		openImageUpload: false,
	}),
	getters: {
		isAIEnabled(): boolean {
			return !!builderSettings.doc?.ai_api_key;
		},
	},
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
					capture("builder_homepage_set");
					toast.success("Homepage set successfully");
				});
		},
		unsetHomePage() {
			return builderSettings.setValue
				.submit({
					home_page: "",
				})
				.then(() => {
					capture("builder_homepage_unset");
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
