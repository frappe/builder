<template>
	<div class="toolbar bg-white p-2 flex justify-center h-14 shadow-sm">
		<div class="absolute left-3 flex items-center mt-2">
			<img src="/favicon.png" alt="logo" class="h-6">
			<h1 class="font-semibold text-gray-600 dark:text-gray-500 text-base ml-1">
				pages
			</h1>
		</div>
	</div>
	<section class="max-w-800 m-auto flex w-3/4 flex-wrap gap-y-4 gap-x-3 pt-10">
		<router-link
				:to="{ name: 'builder', params: { page_id: 'new' } }">
			<div class="auto mr-2 w-56 rounded-md border-2 border-gray-200 p-2">
				<span class="mt-2 text-sm">+ New Page</span>
			</div>
		</router-link>
	</section>

	<section class="max-w-800 m-auto flex w-3/4 flex-col pt-10">
		<h1 class="mb-2 font-bold uppercase text-gray-800">Your Pages</h1>
		<div class="flex flex-wrap gap-y-4 gap-x-2">
			<router-link
				v-for="page in pages"
				:key="page.page_name"
				:to="{ name: 'builder', params: { page_id: page.page_name } }">
				<div class="mr-2 w-56 rounded-md border-2 border-gray-200 p-2">
					<img
						src="https://user-images.githubusercontent.com/13928957/212847544-5773795d-2fd6-48d1-8423-b78ecc92522b.png"
						class="h-28 rounded-sm object-cover" />
					<span class="mt-2 text-sm text-gray-700">
						{{ page.page_name }}
					</span>
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
