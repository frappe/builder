<template>
	<div class="toolbar flex h-14 justify-center bg-white p-2 shadow-sm dark:bg-zinc-900">
		<div class="absolute left-3 mt-2 flex items-center">
			<img src="/frappe_black.png" alt="logo" class="h-5 dark:hidden" />
			<img src="/frappe_white.png" alt="logo" class="hidden h-5 dark:block" />
			<h1 class="text-base text-gray-800 dark:text-gray-200">Builder</h1>
		</div>
	</div>
	<section class="max-w-800 m-auto mb-32 flex w-3/4 flex-col pt-10">
		<div class="mb-6 flex justify-between">
			<h1 class="mb-2 font-bold text-gray-800 dark:text-zinc-400">Your Pages</h1>
			<router-link :to="{ name: 'builder', params: { pageId: 'new' } }">
				<Button variant="solid" icon-right="plus">New Page</Button>
			</router-link>
		</div>
		<div class="flex flex-wrap gap-6">
			<router-link
				v-for="page in webPages.data"
				:key="page.page_name"
				:to="{ name: 'builder', params: { pageId: page.page_name } }"
				class="max-w-[250px] flex-grow basis-52">
				<div
					class="group relative mr-2 w-full overflow-hidden rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
					<img
						:src="page.preview"
						onerror="this.src='/src/assets/fallback.png'"
						class="w-full rounded-sm bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
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
import { webPages } from "@/data/webPage";
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { confirm } from "@/utils/helpers";

const deletePage = async (page: WebPageBeta) => {
	const confirmed = await confirm(`Are you sure you want to delete Page: ${page.page_name}?`);
	if (confirmed) {
		await webPages.delete.submit(page.name);
	}
};
</script>
