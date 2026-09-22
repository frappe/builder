import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import { commands } from "@/components/Commands";
import EditorDemoActions from "@/components/EditorDemo/EditorDemoActions.vue";
import EditorDemoLogo from "@/components/EditorDemo/EditorDemoLogo.vue";
import { leftPanelTabs } from "@/components/LeftPanelTabs";
import { toolbarItems } from "@/components/ToolbarItems";

// surfaces that only make sense with a server behind them
const hiddenToolbarItems = ["menu", "viewers", "actions", "publish"];
const hiddenLeftPanelTabs = ["Code", "Chat"];
const hiddenCommands = ["go-to-dashboard", "preview", "publish", "duplicate-page"];
// these change components or templates the whole site shares
const hiddenBlockMenuOptions = [
	"save-component",
	"edit-component",
	"sync-component",
	"update-component",
	"save-block-template",
];

export function installEditorDemo() {
	hiddenToolbarItems.forEach(toolbarItems.unregister);
	hiddenLeftPanelTabs.forEach(leftPanelTabs.unregister);
	hiddenCommands.forEach(commands.unregister);
	hiddenBlockMenuOptions.forEach(blockContextMenuOptions.unregister);
	toolbarItems.register({ name: "demo-logo", region: "left", component: EditorDemoLogo, before: "modes" });
	toolbarItems.register({ name: "demo-actions", region: "right", component: EditorDemoActions });
}
