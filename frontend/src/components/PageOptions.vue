<template>
	<div>
		<div class="flex flex-row flex-wrap gap-4">
			<Input
				label="Page Title"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="page.page_title"
				@update:modelValue="(val) => updatePage('page_title', val)" />
			<Input
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				label="Route"
				:modelValue="page.route"
				@update:modelValue="(val) => updatePage('route', val)" />
			<Input
				type="checkbox"
				label="Dynamic Route?"
				:modelValue="page.dynamic_route"
				@update:modelValue="(val) => updatePage('dynamic_route', val)" />

			<!-- Dynamic Route Variables -->
			<CollapsibleSection
				sectionName="Test Dynamic Values"
				:sectionCollapsed="true"
				v-if="page.dynamic_route && dynamicVariables.length"
				class="w-full">
				<Input
					v-for="(variable, index) in dynamicVariables"
					:key="index"
					type="text"
					:label="variable.replace(/_/g, ' ')"
					:modelValue="store.routeVariables[variable]"
					@update:modelValue="(val) => store.setRouteVariable(variable, val)" />
			</CollapsibleSection>
		</div>
	</div>
</template>
<script setup lang="ts">
import { builderSettings } from "@/data/builderSettings";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { computed } from "vue";
import { toast } from "vue-sonner";
import CollapsibleSection from "./CollapsibleSection.vue";
import Input from "./Input.vue";

const store = useStore();
const props = defineProps<{
	page: BuilderPage;
}>();
const dynamicVariables = computed(() => {
	return (props.page.route?.match(/<\w+>/g) || []).map((match) => match.slice(1, -1));
});

const unpublishPage = () => {
	webPages.setValue
		.submit({
			name: props.page.name,
			published: false,
		})
		.then(() => {
			toast.success("Page unpublished");
			store.setPage(props.page.name);
			builderSettings.reload();
		});
};

const setHomePage = (page: BuilderPage) => {
	builderSettings.setValue
		.submit({
			home_page: page.route,
		})
		.then(() => {
			toast.success("Home Page set");
		});
};

const unsetHomePage = () => {
	builderSettings.setValue
		.submit({
			home_page: "",
		})
		.then(() => {
			toast.success("Home Page unset");
		});
};

const updatePage = (key: keyof BuilderPage, value: any) => {
	webPages.setValue
		.submit({
			name: props.page.name,
			[key]: value,
		})
		.then(() => {
			props.page[key] = value;
		});
};
</script>
