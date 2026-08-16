import { __ } from "@/translation";
import BlockContextMenu from "@/components/BlockContextMenu.vue";
import { builderSettings } from "@/data/builderSettings";
import { BuilderSettings } from "@/types/doctypes";
import RealTimeHandler from "@/utils/realtimeHandler";
import { useDark, useStorage } from "@vueuse/core";
import { createResource, toast } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { defineStore } from "pinia";
import BlockLayers from "./components/BlockLayers.vue";

const { capture } = useTelemetry();

declare global {
	interface Window {
		is_fc_site?: boolean | string;
		is_read_only_mode?: boolean | string;
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
		showBlockTemplateDialog: false,
		showTokenManager: false,
		shortcutsModalOpen: false,
		realtime: new RealTimeHandler(),
		readOnlyMode: false,
		// An AI build is streaming onto the canvas: the server owns the draft, so the
		// editor's autosave must stand down (it would persist the partial preview).
		aiBuildingCanvas: false,
		// site-level maintenance/migration state, not the editor's edit lock
		isSiteInReadOnlyMode: window.is_read_only_mode === "True",
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
		// Set from ai_setup_state: a provider carrying its own key (Anthropic, a
		// self-hosted gateway) is enough on its own, and the shared OpenRouter key in
		// Builder Settings is the only thing the client can see for itself.
		// null until the server answers; false means "asked, not configured"
		aiConfigured: <boolean | null>null,
	}),
	getters: {
		isAIEnabled(): boolean {
			return !!this.aiConfigured || !!builderSettings.doc?.ai_api_key;
		},
		// unknown until a positive signal or the server's verdict arrives
		isAIStateKnown(): boolean {
			return this.aiConfigured !== null || this.isAIEnabled;
		},
	},
	actions: {
		async refreshAIState() {
			const state = (await createResource({ url: "builder.ai.api.ai_setup_state" })
				.submit()
				.catch(() => null)) as { configured?: boolean } | null;
			this.aiConfigured = !!state?.configured;
		},
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
					toast.success(__("Homepage set successfully"));
				});
		},
		unsetHomePage() {
			return builderSettings.setValue
				.submit({
					home_page: "",
				})
				.then(() => {
					capture("builder_homepage_unset");
					toast.success(__("This page will no longer be the homepage"));
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
		openBuilderSettings(tab?: string) {
			if (tab) {
				this.settingsActiveTab = tab;
			}
			this.showSettingsDialog = true;
		},
	},
});

export default useBuilderStore;
