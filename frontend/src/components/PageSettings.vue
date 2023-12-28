<template>
	<div>
		<div class="flex flex-row flex-wrap gap-5">
			<h3 class="mb-1 w-full text-xs font-bold uppercase text-gray-600">Page Options</h3>
			<InlineInput
				label="Title"
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				:modelValue="pageData.page_title"
				@update:modelValue="(val) => webPages.setValue.submit({ name: pageData.name, page_title: val })" />
			<InlineInput
				type="text"
				class="w-full text-sm [&>label]:w-[60%] [&>label]:min-w-[180px]"
				label="Route"
				:modelValue="pageData.route"
				@update:modelValue="(val) => webPages.setValue.submit({ name: pageData.name, route: val })" />
			<!-- is Dynamic Route -->
			<InlineInput
				label="Dynamic Route?"
				class="w-full text-sm"
				type="checkbox"
				:modelValue="pageData.dynamic_route"
				@update:modelValue="(val) => webPages.setValue.submit({ name: pageData.name, dynamic_route: val })" />
			<!-- Dynamic Route Variables -->
			<div v-if="pageData.dynamic_route" class="w-full">
				<h3 class="mt-5 text-xs font-bold uppercase text-gray-600">Route Values</h3>
				<div class="mt-5 flex flex-row flex-wrap gap-5">
					<InlineInput
						v-for="(variable, index) in dynamicVariables"
						:key="index"
						type="text"
						:label="variable"
						class="w-full text-sm"
						:modelValue="store.routeVariables[variable]"
						@update:modelValue="(val) => store.setRouteVariable(variable, val)" />
				</div>
			</div>
			<div class="flex w-full flex-col gap-2">
				<Button
					v-if="pageData.published"
					@click="() => store.openPageInBrowser()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					View Page
				</Button>
				<Button
					v-if="pageData.published"
					@click="() => unpublishPage()"
					class="block text-base dark:bg-zinc-800 dark:text-zinc-200 dark:hover:bg-zinc-700">
					Unpublish Page
				</Button>
				<Button
					@click="() => store.openInDesk(pageData)"
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
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { computed } from "vue";
import { toast } from "vue-sonner";
import InlineInput from "./InlineInput.vue";

const store = useStore();
const pageData = computed(() => store.getActivePage());
const dynamicVariables = computed(() => {
	const variables = (pageData.value.route?.match(/<\w+>/g) || []).map((match) => match.slice(1, -1));
	return variables.map((variable) => variable.replace("_", " "));
});

const unpublishPage = () => {
	webPages.setValue
		.submit({
			name: pageData.value.name,
			published: false,
		})
		.then(() => {
			toast.success("Page unpublished");
			store.setPageData();
		});
};
</script>
