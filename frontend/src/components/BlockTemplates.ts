import type { BlockTemplate } from "@/types/doctypes";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component } from "vue";

/** A block template that a plugin adds to the Block Templates panel, beside the Block Template documents. */
export type PluginBlockTemplate = RegistryItem & {
	label: string;
	/** a category the panel has, or a new one, which shows after Builder's own */
	category: string;
	/** an image URL, shown as the card's preview */
	preview?: string;
	/** a lucide class name, or a component, shown when there is no preview */
	icon?: string | Component;
	/** called on each insert, and synchronously, because a drag sets its data in dragstart */
	getBlock: () => BlockOptions;
};

export const blockTemplates = createRegistry<PluginBlockTemplate>();

export type BlockTemplateSection = {
	category: string;
	templates: BlockTemplate[];
	pluginTemplates: PluginBlockTemplate[];
};

export function getBlockTemplateSections(
	categories: string[],
	templates: BlockTemplate[],
	pluginTemplates: PluginBlockTemplate[],
	filter = "",
): BlockTemplateSection[] {
	const matches = (text?: string) => !filter || Boolean(text?.toLowerCase().includes(filter.toLowerCase()));
	const pluginCategories = pluginTemplates.map((template) => template.category);
	return [...new Set([...categories, ...pluginCategories])]
		.map((category) => ({
			category,
			templates: templates.filter((template) => template.category === category && matches(template.name)),
			pluginTemplates: pluginTemplates.filter(
				(template) => template.category === category && matches(template.label),
			),
		}))
		.filter((section) => section.templates.length || section.pluginTemplates.length);
}
