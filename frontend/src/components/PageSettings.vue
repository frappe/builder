<template>
	<div>
		<div class="flex flex-row flex-wrap gap-5">
			<h3 class="mb-1 w-full text-sm font-medium text-gray-900 dark:text-zinc-300">Page Options</h3>
			<InlineInput
				label="Title"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="page.page_title"
				@update:modelValue="(val) => webPages.setValue.submit({ name: page.name, page_title: val })" />
			<InlineInput
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				label="Route"
				:modelValue="page.route"
				@update:modelValue="(val) => webPages.setValue.submit({ name: page.name, route: val })" />
			<!-- is Dynamic Route -->
			<InlineInput
				label="Dynamic Route?"
				class="w-full text-sm"
				type="checkbox"
				:modelValue="page.dynamic_route"
				@update:modelValue="(val) => webPages.setValue.submit({ name: page.name, dynamic_route: val })" />
			<!-- Dynamic Route Variables -->
			<div v-if="page.dynamic_route" class="mb-3 mt-3 w-full">
				<h3 class="text-xs font-bold uppercase text-gray-600">Route Values</h3>
				<div class="mt-5 flex flex-row flex-wrap gap-5">
					<InlineInput
						v-for="(variable, index) in dynamicVariables"
						:key="index"
						type="text"
						:label="variable.replace(/_/g, ' ')"
						class="w-full text-sm"
						:modelValue="store.routeVariables[variable]"
						@update:modelValue="(val) => store.setRouteVariable(variable, val)" />
				</div>
			</div>
			<div class="flex w-full flex-col gap-2">
				<Button
					v-if="page.published"
					@click="() => store.openPageInBrowser(page)"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					View Published Page
				</Button>
				<Button
					v-if="page.published"
					:disabled="isHomePage(page)"
					@click="() => setHomePage(page)"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Set as Home Page
				</Button>
				<Button
					v-if="page.published"
					@click="() => unpublishPage()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Unpublish Page
				</Button>
				<hr class="my-2 dark:border-zinc-800" v-if="page.published" />
				<Button
					@click="() => store.openInDesk(page)"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Open in Desk
				</Button>
				<Button
					@click="() => store.openBuilderSettings()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Open Builder Settings
				</Button>
			</div>
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
import InlineInput from "./InlineInput.vue";

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

const isHomePage = (page: BuilderPage) => {
	return builderSettings.doc.home_page === page.route;
};
</script>
