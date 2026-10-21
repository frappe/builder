import { leftPanelTabs, lucideIcon, useBuilderStore, type ExtensionContext } from "builder";
import type { App } from "vue";
import "./index.css";
import Panel from "./Panel.vue";

export default {
	install(_app: App, context: ExtensionContext) {
		leftPanelTabs.register({
			name: __EXTENSION_SLUG_JSON__,
			label: __LABEL_JSON__,
			icon: lucideIcon("lucide-blocks"),
			// the panel acts on the selected block, so it stays open when the user selects one
			keepOpenOnSelection: true,
			component: Panel,
		});
		// the Open button in the extension's details page shows this tab
		context.setOpenHandler(() => (useBuilderStore().leftPanelActiveTab = __EXTENSION_SLUG_JSON__));
	},
};
