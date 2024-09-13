<template>
	<div>
		<div class="flex flex-row flex-wrap gap-4">
			<Input
				label="Page Title"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="page.page_title"
				@update:modelValue="(val: string) => store.updateActivePage('page_title', val)" />
			<Input
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px] [&>p]:text-p-xs"
				label="Route"
				description="The URL path for this page. For variables, use colon (e.g. /users/:id)"
				@input="(val: string) => (page.route = val)"
				:modelValue="page.route"
				:hideClearButton="true"
				@update:modelValue="(val: string) => store.updateActivePage('route', val)" />
			<!-- Dynamic Route Variables -->
			<CollapsibleSection
				sectionName="URL Variables"
				v-if="dynamicVariables.length"
				class="w-full [&>div>h3]:!text-xs [&>div>h3]:!text-text-icons-gray-5">
				<Input
					v-for="(variable, index) in dynamicVariables"
					:key="index"
					type="text"
					:label="variable.replace(/_/g, ' ')"
					:modelValue="store.routeVariables[variable]"
					@update:modelValue="(val: string) => store.setRouteVariable(variable, val)" />
			</CollapsibleSection>
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { getRouteVariables } from "@/utils/helpers";
import { computed } from "vue";
import CollapsibleSection from "./CollapsibleSection.vue";

const store = useStore();
const props = defineProps<{
	page: BuilderPage;
}>();
const dynamicVariables = computed(() => {
	return getRouteVariables(props.page.route || "");
});
</script>
