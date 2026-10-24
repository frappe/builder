/**
 * The editor's public API for plugins, which import it as "builder".
 *
 * Only what is exported here is reachable from a plugin, so a change to an
 * export breaks plugins and everything else can change freely.
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
export { lucideIcon } from "@/plugins/lucideIcon";

// the controls of the property panel, so a plugin's section looks like Builder's own
export { default as AttributePropertyControl } from "@/components/Controls/AttributePropertyControl.vue";
export { default as BasePropertyControl } from "@/components/Controls/BasePropertyControl.vue";
export { default as StylePropertyControl } from "@/components/Controls/StylePropertyControl.vue";
export { default as ColorInput } from "@/components/Controls/ColorInput.vue";
export { default as OptionToggle } from "@/components/Controls/OptionToggle.vue";
export { default as RangeInput } from "@/components/Controls/RangeInput.vue";
export type { PluginContext, PluginState } from "@/plugins/context";
