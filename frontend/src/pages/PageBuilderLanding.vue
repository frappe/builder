<template>
	<div class="toolbar flex h-14 justify-center bg-white p-2 shadow-sm dark:bg-zinc-900">
		<div class="absolute left-3 mt-2 flex items-center">
			<img src="/frappe_black.png" alt="logo" class="h-5 dark:hidden" />
			<img src="/frappe_white.png" alt="logo" class="hidden h-5 dark:block" />
			<h1 class="text-base text-gray-800 dark:text-gray-200">Builder</h1>
		</div>
	</div>
	<section class="max-w-800 m-auto flex w-3/4 flex-wrap gap-x-3 gap-y-4 pt-10">
		<router-link :to="{ name: 'builder', params: { pageId: 'new' } }">
			<div
				class="auto group mr-2 flex w-56 justify-between rounded-md p-3 text-sm shadow dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-400">
				<span class="group-hover:dark:text-zinc-200">New Page</span>
				<span class="font-semibold group-hover:dark:text-zinc-200">+</span>
			</div>
		</router-link>
	</section>
	<section class="max-w-800 m-auto mb-32 flex w-3/4 flex-col pt-10">
		<h1 class="mb-2 font-bold uppercase text-gray-800 dark:text-zinc-400">Your Pages</h1>
		<div class="flex flex-wrap gap-x-2 gap-y-4">
			<router-link
				v-for="page in pages"
				:key="page.page_name"
				:to="{ name: 'builder', params: { pageId: page.page_name } }">
				<div
					class="group relative mr-2 w-[224px] rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
					<img
						:src="page.preview"
						onerror="this.src='https://user-images.githubusercontent.com/13928957/212847544-5773795d-2fd6-48d1-8423-b78ecc92522b.png'"
						class="h-[132px] rounded-sm bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
					<p
						class="border-t-[1px] px-3 py-2 text-sm text-gray-700 dark:border-zinc-800 dark:text-zinc-400 group-hover:dark:text-zinc-200">
						{{ page.page_title || page.page_name }}
					</p>
					<FeatherIcon
						name="trash"
						class="absolute right-2 top-2 hidden h-8 w-8 rounded bg-white p-2 group-hover:block dark:bg-zinc-900 dark:text-zinc-200"
						@click.stop.prevent="deletePage(page)"></FeatherIcon>
				</div>
			</router-link>
		</div>
	</section>
</template>
<script setup lang="ts">
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { confirm } from "@/utils/helpers";
import { createListResource } from "frappe-ui";
import { ref, Ref } from "vue";

const pages = ref([]) as Ref<WebPageBeta[]>;

const pagesResource = createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "page_name", "route", "preview", "page_title"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 100,
	auto: true,
	onSuccess(data: WebPageBeta[]) {
		pages.value = data;
	},
});

const deletePage = async (page: WebPageBeta) => {
	const confirmed = await confirm(`Are you sure you want to delete Page: ${page.page_name}?`);
	if (confirmed) {
		await pagesResource.delete.submit(page.name);
	}
};
</script>
