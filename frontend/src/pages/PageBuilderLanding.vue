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
			<h1 class="mb-2 font-bold text-gray-800 dark:text-zinc-400">My Pages</h1>
			<router-link :to="{ name: 'builder', params: { pageId: 'new' } }">
				<Button variant="solid" icon-left="plus">New</Button>
			</router-link>
		</div>
		<div class="flex flex-wrap gap-6">
			<div v-if="!webPages.data || !webPages.data.length" class="flex flex-col items-center justify-center">
				<p class="mt-4 text-center text-gray-500">
					You don't have any pages yet. Click on the "+ New" button to create a new page.
				</p>
			</div>
			<router-link
				v-for="page in webPages.data"
				:key="page.page_name"
				:to="{ name: 'builder', params: { pageId: page.page_name } }"
				class="max-w-[250px] flex-grow basis-52">
				<div
					class="group relative mr-2 w-full overflow-hidden rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
					<img
						width="250"
						height="140"
						:src="page.preview"
						onerror="this.src='/assets/website_builder/images/fallback.png'"
						class="w-full rounded-sm bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
					<div class="flex items-center justify-between border-t-[1px] px-3 dark:border-zinc-800">
						<p class="py-2 text-sm text-gray-700 dark:text-zinc-200">
							{{ page.page_title || page.page_name }}
							<Badge v-show="page.draft_blocks">Draft</Badge>
							<UseTimeAgo v-slot="{ timeAgo }" :time="page.creation">
								<span class="mt-1 block text-xs text-gray-500">
									{{ timeAgo }}
								</span>
							</UseTimeAgo>
						</p>
						<Dropdown
							:options="[
								{ label: 'Duplicate', onClick: () => duplicatePage(page), icon: 'copy' },
								{ label: 'View in Desk', onClick: () => openInDesk(page), icon: 'arrow-up-right' },
								{ label: 'Delete', onClick: () => deletePage(page), icon: 'trash' },
							]"
							placement="right">
							<template v-slot="{ open }">
								<FeatherIcon
									name="more-vertical"
									class="h-4 w-4 text-gray-500 group-hover:text-gray-700"
									@click="open"></FeatherIcon>
							</template>
						</Dropdown>
					</div>
				</div>
			</router-link>
		</div>
	</section>
</template>
<script setup lang="ts">
import { webPages } from "@/data/webPage";
import { WebPageBeta } from "@/types/WebsiteBuilder/WebPageBeta";
import { confirm } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Badge, Dropdown } from "frappe-ui";
import { onActivated } from "vue";

const deletePage = async (page: WebPageBeta) => {
	const confirmed = await confirm(`Are you sure you want to delete Page: ${page.page_name}?`);
	if (confirmed) {
		await webPages.delete.submit(page.name);
	}
};

const duplicatePage = async (page: WebPageBeta) => {
	const pageCopy = { ...page };
	pageCopy.page_name = `${page.page_name}-copy`;
	pageCopy.page_title = `${page.page_title} Copy`;
	await webPages.insert.submit(pageCopy);
};

const openInDesk = (page: WebPageBeta) => {
	window.open(`/app/web-page-beta/${page.page_name}`, "_blank");
};

onActivated(() => {
	webPages.fetch();
});
</script>
