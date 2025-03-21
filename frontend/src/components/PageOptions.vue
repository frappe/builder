<template>
	<div>
		<div class="flex flex-row flex-wrap gap-4">
			<BuilderInput
				label="Page Title"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="page.page_title"
				@update:modelValue="(val: string) => pageStore.updateActivePage('page_title', val)" />
			<BuilderInput
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px] [&>p]:text-p-xs"
				label="Route"
				description="The URL path for this page. For variables, use colon (e.g. /users/:id)"
				@input="(val: string) => (page.route = val)"
				:modelValue="page.route"
				:hideClearButton="true"
				@update:modelValue="(val: string) => pageStore.updateActivePage('route', val)" />
			<!-- Dynamic Route Variables -->
			<CollapsibleSection
				sectionName="URL Variables"
				v-if="dynamicVariables.length"
				class="w-full [&>div>h3]:!text-xs [&>div>h3]:!text-ink-gray-5">
				<BuilderInput
					v-for="(variable, index) in dynamicVariables"
					:key="index"
					type="text"
					:label="variable.replace(/_/g, ' ')"
					:modelValue="pageStore.routeVariables[variable]"
					@update:modelValue="(val: string) => pageStore.setRouteVariable(variable, val)" />
			</CollapsibleSection>
		</div>
	</div>
</template>
<script setup lang="ts">
import usepageStore from "@/stores/pageStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getRouteVariables } from "@/utils/helpers";
import { computed } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const pageStore = usepageStore();
const props = defineProps<{
	page: BuilderPage;
}>();
const dynamicVariables = computed(() => {
	return getRouteVariables(props.page.route || "");
});
</script>
