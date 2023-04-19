<template>
	<section class="m-auto flex w-3/4 justify-center pt-10">
		<div
			v-for="page of pages"
			:key="page.page_name"
			class="mr-2 h-24 w-56 rounded-md border-2 border-gray-200 bg-gray-100 p-2">
			{{ page.page_name }}
		</div>
	</section>
</template>
<script setup lang="ts">
import { createListResource } from "frappe-ui";
import { ref } from "vue";
let pages = ref([]);

createListResource({
	doctype: "Web Page Beta",
	fields: ["name", "blocks", "page_name", "route"],
	orderBy: "creation desc",
	start: 0,
	pageLength: 10,
	auto: true,
	onSuccess(data: Array<any>) {
		pages.value = data;
		// setPage(store.pages[localStorage.getItem("selectedPage") || "home"])
	},
});
</script>
