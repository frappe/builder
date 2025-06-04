<template>
	<div v-if="blockController.isBlockSelected()" class="flex select-none flex-col pb-16">
		<div class="sticky top-0 z-50 mt-[-16px] flex w-full bg-surface-white py-3">
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
		<div class="flex flex-col gap-3">
			<CollapsibleSection
				:sectionName="section.name"
				v-for="section in sections"
				v-show="showSection(section)"
				:key="section.name"
				:sectionCollapsed="toValue(section.collapsed) && !builderStore.propertyFilter">
				<template v-for="property in getFilteredProperties(section)">
					<component :is="property.component" v-bind="property.getProps()" v-on="property.events || {}">
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
import customAttributesSection from "@/components/BlockPropertySections/CustomAttributesSection";
import dataKeySection from "@/components/BlockPropertySections/DataKeySection";
import dimensionSection from "@/components/BlockPropertySections/DimenstionSection";
import formOptionsSection from "@/components/BlockPropertySections/FormOptionsSection";
import imageOptionsSection from "@/components/BlockPropertySections/ImageOptionsSection";
import inputPropertiesSection from "@/components/BlockPropertySections/InputPropertiesSection";
import layoutSection from "@/components/BlockPropertySections/LayoutSection";
import linkSection from "@/components/BlockPropertySections/LinkSection";
import optionsSection from "@/components/BlockPropertySections/OptionsSection";
import positionSection from "@/components/BlockPropertySections/PositionSection";
import rawStyleSection from "@/components/BlockPropertySections/RawStyleSection";
import spacingSection from "@/components/BlockPropertySections/SpacingSection";
import styleSection from "@/components/BlockPropertySections/StyleSection";
import typographySection from "@/components/BlockPropertySections/TypographySection";
import videoOptionsSection from "@/components/BlockPropertySections/VideoOptionsSection";
import useBuilderStore from "@/stores/builderStore";
import blockController from "@/utils/blockController";
import { toValue } from "@vueuse/core";
import { Ref, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const builderStore = useBuilderStore();

type PropertySection = {
	name: string;
	properties: BlockProperty[];
	condition?: () => boolean;
	collapsed?: boolean;
};

const searchInput = ref(null) as Ref<HTMLElement | null>;

const showSection = (section: PropertySection) => {
	let showSection = true;
	if (section.condition) {
		showSection = section.condition();
	}
	if (showSection && builderStore.propertyFilter) {
		showSection = getFilteredProperties(section).length > 0;
	}
	return showSection;
};

const getFilteredProperties = (section: PropertySection) => {
	return section.properties.filter((property) => {
		let showProperty = true;
		if (property.condition) {
			showProperty = property.condition();
		}
		if (showProperty && builderStore.propertyFilter) {
			showProperty =
				section.name.toLowerCase().includes(builderStore.propertyFilter.toLowerCase()) ||
				property.searchKeyWords?.toLowerCase().includes(builderStore.propertyFilter.toLowerCase());
		}
		return showProperty;
	});
};

const sections = [
	linkSection,
	formOptionsSection,
	layoutSection,
	inputPropertiesSection,
	imageOptionsSection,
	videoOptionsSection,
	typographySection,
	styleSection,
	dimensionSection,
	positionSection,
	spacingSection,
	optionsSection,
	dataKeySection,
	customAttributesSection,
	rawStyleSection,
] as PropertySection[];
</script>
