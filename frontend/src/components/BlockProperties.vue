<template>
	<div v-if="blockController.isBlockSelected()" class="isolate flex select-none flex-col pb-16">
		<div class="sticky top-0 z-[1] mt-[-16px] flex w-full bg-surface-base py-3">
			<BuilderInput
				ref="searchInput"
				type="text"
				:placeholder="__('Search properties')"
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
		<p class="mt-2 text-center text-sm text-ink-gray-6">{{ __("Select a block to edit properties") }}</p>
	</div>
</template>
<script setup lang="ts">
import { propertySections, type PropertySection } from "@/components/BlockPropertySections";
import useBuilderStore from "@/stores/builderStore";
import blockController from "@/utils/blockController";
import { toValue } from "@vueuse/core";
import { Ref, ref } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const builderStore = useBuilderStore();

const sections = propertySections.visible;

const searchInput = ref(null) as Ref<HTMLElement | null>;

// the registry applies section.condition, so only the "every property is hidden"
// case is left here (a blank header otherwise)
const showSection = (section: PropertySection) => getFilteredProperties(section).length > 0;

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
</script>
