import { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
import { commands } from "@/components/Commands";
import { editorDemoStage } from "@/components/EditorDemo/editorDemoStage";
import EditorDemoActions from "@/components/EditorDemo/EditorDemoActions.vue";
import EditorDemoLogo from "@/components/EditorDemo/EditorDemoLogo.vue";
import { leftPanelTabs } from "@/components/LeftPanelTabs";
import { toolbarItems } from "@/components/ToolbarItems";
import { __ } from "@/translation";
import { onLauncherMessage, postToLauncher } from "@/utils/editorDemo";
import { toast } from "frappe-ui";
import { onMounted } from "vue";

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

	onMounted(() => {
		editorDemoStage.start();
		if (!editorDemoStage.framed) return showEditingTip();
		onLauncherMessage(({ type, scrollY = 0, target, dark = false }) => {
			if (type === "prepare") editorDemoStage.prepare(scrollY, target, dark);
			if (type === "play") editorDemoStage.play().then(showEditingTip);
			if (type === "close") editorDemoStage.exit();
		});
		postToLauncher({ type: "booted" });
	});
}

let tipShown = false;

function showEditingTip() {
	if (tipShown) return;
	tipShown = true;
	toast.info(__("Double-click any text to edit it"), { duration: 6000 });
}
