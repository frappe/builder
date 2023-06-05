<template>
	<div class="m-auto flex w-[80%] max-w-lg flex-col py-20">
		<div class="flex items-center">
			<!-- <FeatherIcon name="chevron-left" class="w-5 h-5 mr-3"></FeatherIcon> -->
			<h1 class="font-bold">Page Settings</h1>
		</div>
		<div class="flex w-full flex-col">
			<div class="mt-12 flex items-center gap-5">
				<Input type="text" class="w-full" label="Page Title" v-model="pageData.title" />
				<Input type="text" class="w-full" label="URL" v-model="pageData.route" />
			</div>
			<div class="mt-4 flex gap-3">
				<Input type="textarea" class="w-full" label="Description"></Input>
			</div>
		</div>
	</div>
</template>
<script setup lang="ts">
import useStore from "@/store";
const store = useStore();
import { createDocumentResource } from "frappe-ui";
import { Ref, ref } from "vue";
import { useRoute } from "vue-router";
const route = useRoute();

const pageData = ref({}) as unknown as Ref<WebPageBeta>;
const page = createDocumentResource({
	method: "GET",
	doctype: "Web Page Beta",
	name: route.params.pageId,
	auto: true,
	onSuccess(_page: any) {
		pageData.value = _page;
	},
});
</script>
