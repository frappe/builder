<template>
	<div class="flex min-h-[50vh] flex-wrap gap-6">
		<div
			@click="() => loadPage('new')"
			class="group relative mr-2 h-fit w-full max-w-[250px] flex-grow basis-52 overflow-hidden rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
			<img
				width="250"
				height="140"
				:src="'/assets/builder/images/fallback.png'"
				class="w-full overflow-hidden rounded-lg bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
			<div class="flex items-center justify-between border-t-[1px] px-3 dark:border-zinc-800">
				<span class="inline-block max-w-[160px] py-2 text-sm text-gray-700 dark:text-zinc-200">
					<div class="flex items-center gap-1">
						<p class="truncate">Blank</p>
					</div>
				</span>
			</div>
		</div>
		<TemplatePagePreview
			class="h-fit max-w-[250px] flex-grow basis-52"
			v-for="page in templates.data"
			:page="page"
			@click="(p) => duplicatePage(p)"></TemplatePagePreview>
	</div>
</template>
<script setup lang="ts">
import { templates, webPages } from "@/data/webPage";
import router from "@/router";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { createDocumentResource } from "frappe-ui";
import TemplatePagePreview from "./TemplatePagePreview.vue";

const emit = defineEmits(["templateSelected"]);

const loadPage = async (pageName: string = "new") => {
	emit("templateSelected", null);
	await new Promise((resolve) => setTimeout(resolve, 500));
	router.push({ name: "builder", params: { pageId: pageName } });
};

const duplicatePage = async (page?: BuilderPage) => {
	if (!page) {
		return emit("templateSelected", null);
	}
	const webPageResource = await createDocumentResource({
		doctype: "Builder Page",
		name: page.page_name,
		auto: true,
	});
	await webPageResource.get.promise;

	const pageCopy = webPageResource.doc as BuilderPage;
	pageCopy.page_title = `${pageCopy.page_title}`;
	pageCopy.is_template = 0;
	const newPage = await webPages.insert.submit(pageCopy);
	loadPage(newPage.name);
};
</script>
