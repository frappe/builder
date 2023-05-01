<template>
	<div class="toolbar flex h-14 justify-center bg-white p-2 shadow-sm dark:bg-zinc-900">
		<div class="absolute left-3 mt-2 flex items-center">
			<img src="/favicon.png" alt="logo" class="h-6" />
			<h1 class="ml-1 text-base font-semibold text-gray-600 dark:text-gray-500">pages</h1>
		</div>
	</div>
	<section class="max-w-800 m-auto flex w-3/4 flex-wrap gap-y-4 gap-x-3 pt-10">
		<router-link :to="{ name: 'builder', params: { pageId: 'new' } }">
			<div
				class="auto mr-2 flex w-56 justify-between rounded-md border-[1px] border-gray-200 p-3 text-sm dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
				<span>New Page</span>
				<span>+</span>
			</div>
		</router-link>
	</section>

	<section class="max-w-800 m-auto flex w-3/4 flex-col pt-10">
		<h1 class="mb-2 font-bold uppercase text-gray-800 dark:text-zinc-400">Your Pages</h1>
		<div class="flex flex-wrap gap-y-4 gap-x-2">
			<router-link
				v-for="page in pages"
				:key="page.page_name"
				:to="{ name: 'builder', params: { pageId: page.page_name } }">
				<div
					class="mr-2 w-56 rounded-md border-[1px] border-gray-200 dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
					<img
						src="https://user-images.githubusercontent.com/13928957/212847544-5773795d-2fd6-48d1-8423-b78ecc92522b.png"
						class="h-28 rounded-sm object-cover" />
					<p class="mt-2 px-3 pb-2 text-sm text-gray-700 dark:text-zinc-300">
						{{ page.page_name }}
					</p>
				</div>
			</router-link>
		</div>
	</section>
</template>
<script setup lang="ts">
import { createListResource } from "frappe-ui";
import { ref, Ref } from "vue";

const pages = ref([]) as Ref<Page[]>;

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "page_name", "route"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 10,
	auto: true,
	onSuccess(data: Page[]) {
		pages.value = data;
	},
});
</script>
