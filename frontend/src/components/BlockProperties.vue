<template>
	<div v-if="blockController.isBlockSelected()" class="isolate flex select-none flex-col pb-16">
		<div class="sticky top-0 z-[1] mt-[-16px] flex w-full bg-surface-base py-3">
			<BuilderInput
				ref="searchInput"
				type="text"
				placeholder="Search properties"
				v-model="builderStore.propertyFilter"
				@input="
					(value: string) => {
						builderStore.propertyFilter = value;
					}
				" />
		</div>
		<div class="mt-2 flex flex-col gap-3">
			<CollapsibleSection
				:sectionName="section.name"
				v-for="section in sections"
				v-show="showSection(section)"
				:key="section.name"
				:sectionCollapsed="toValue(section.collapsed) && !builderStore.propertyFilter">
				<template v-for="property in getFilteredProperties(section)">
					<component :is="property.component" v-bind="property.getProps?.()" v-on="property.events || {}">
						{{ property.innerText || "" }}
					</component>
				</template>
			</CollapsibleSection>
		</div>
	</div>
	<div v-else>
		<p class="mt-2 text-center text-sm text-ink-gray-6">Select a block to edit properties</p>
	</div>
</template>
<script setup lang="ts">
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
import useBuilderStore from "@/stores/builderStore";
import blockController from "@/utils/blockController";
import { toValue } from "@vueuse/core";
import type { Component } from "vue";
import { Ref, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const builderStore = useBuilderStore();

type BlockProperty = {
	component: Component;
	getProps?: () => Record<string, unknown>;
	events?: Record<string, unknown>;
	searchKeyWords: string;
	condition?: () => boolean;
	innerText?: string;
};

type PropertySection = {
	name: string;
	properties: BlockProperty[] | (() => BlockProperty[]);
	condition?: () => boolean;
	collapsed?: boolean;
};

const searchInput = ref(null) as Ref<HTMLElement | null>;

const showSection = (section: PropertySection) => {
	let showSection = true;
	if (section.condition) {
		showSection = section.condition();
	}
	// hide sections whose properties are all condition-hidden (blank header otherwise)
	if (showSection) {
		showSection = getFilteredProperties(section).length > 0;
	}
	return showSection;
};

const getFilteredProperties = (section: PropertySection) => {
	const properties = typeof section.properties === "function" ? section.properties() : section.properties;
	return properties.filter((property) => {
		let showProperty = true;
		if (property.condition) {
			showProperty = property.condition();
		}
		if (showProperty && builderStore.propertyFilter) {
			const searchTerm = builderStore.propertyFilter.toLowerCase();
			showProperty =
				section.name?.toLowerCase().includes(searchTerm) ||
				property.searchKeyWords?.toLowerCase().includes(searchTerm);
		}
		return showProperty;
	});
};

const sections = [
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
</script>
