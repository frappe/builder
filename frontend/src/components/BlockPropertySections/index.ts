import accessibilitySection from "@/components/BlockPropertySections/AccessibilitySection";
import collectionOptionsSection from "@/components/BlockPropertySections/CollectionOptionsSection";
import customAttributesSection from "@/components/BlockPropertySections/CustomAttributesSection";
import dataKeySection from "@/components/BlockPropertySections/DataKeySection";
import dimensionSection from "@/components/BlockPropertySections/DimensionSection";
import editorConfigSection from "@/components/BlockPropertySections/EditorConfigSection";
import HTMLOptionsSection from "@/components/BlockPropertySections/HTMLOptionsSection";
import imageOptionsSection from "@/components/BlockPropertySections/ImageOptionsSection";
import inputOptionsSection from "@/components/BlockPropertySections/InputOptionsSection";
import layoutSection from "@/components/BlockPropertySections/LayoutSection";
import linkSection from "@/components/BlockPropertySections/LinkSection";
import moreStylesSection from "@/components/BlockPropertySections/MoreStylesSection";
import optionsSection from "@/components/BlockPropertySections/OptionsSection";
import positionSection from "@/components/BlockPropertySections/PositionSection";
import spacingSection from "@/components/BlockPropertySections/SpacingSection";
import standardPropsInputSection from "@/components/BlockPropertySections/StandardPropsInputSection";
import styleSection from "@/components/BlockPropertySections/StyleSection";
import transitionSection from "@/components/BlockPropertySections/TransitionSection";
import typographySection from "@/components/BlockPropertySections/TypographySection";
import videoOptionsSection from "@/components/BlockPropertySections/VideoOptionsSection";
import { createRegistry, type RegistryItem } from "@/utils/createRegistry";
import type { Component, ComputedRef } from "vue";

export type BlockProperty = {
	component: Component;
	getProps?: () => Record<string, unknown>;
	events?: Record<string, unknown>;
	searchKeyWords: string;
	condition?: () => boolean;
	innerText?: string;
	usedStyleProperties?: string[];
};

export type PropertySection = RegistryItem & {
	properties: BlockProperty[] | (() => BlockProperty[]);
	collapsed?: boolean | ComputedRef<boolean>;
};

export const propertySections = createRegistry<PropertySection>();
export const registerPropertySection = propertySections.register;

// exported for stylePropertiesWithControls, which needs every built-in section
// regardless of condition and runs before the panel mounts
export const builtInSections = [
	standardPropsInputSection,
	collectionOptionsSection,
	linkSection,
	layoutSection,
	imageOptionsSection,
	HTMLOptionsSection,
	videoOptionsSection,
	inputOptionsSection,
	typographySection,
	styleSection,
	dimensionSection,
	spacingSection,
	transitionSection,
	optionsSection,
	positionSection,
	dataKeySection,
	accessibilitySection,
	customAttributesSection,
	editorConfigSection,
	moreStylesSection,
] as PropertySection[];

export function registerBuiltInPropertySections() {
	builtInSections.forEach((section) => registerPropertySection(section));
}
