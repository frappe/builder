/**
 * The editor's public API for extensions, which import it as "builder".
 *
 * Only what is exported here is reachable from an extension, so a change to an
 * export breaks extensions and everything else can change freely.
 */

export { leftPanelTabs, type LeftPanelTab } from "@/components/LeftPanelTabs";
export { toolbarItems, type ToolbarItem } from "@/components/ToolbarItems";
export { blockContextMenuOptions } from "@/components/BlockContextMenuOptions";
export type { ContextMenuOption } from "@/types/blockContextMenu";
export { propertySections, type PropertySection } from "@/components/BlockPropertySections";
export { settingsItems, type SettingsItem } from "@/components/Settings";
export { default as usePageStore } from "@/stores/pageStore";
export { default as useCanvasStore } from "@/stores/canvasStore";
export { default as useBuilderStore } from "@/stores/builderStore";
export { default as blockController } from "@/utils/blockController";
export { default as Block } from "@/block";
