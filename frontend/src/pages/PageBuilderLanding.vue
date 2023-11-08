<template>
	<div
		class="toolbar flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"
		ref="toolbar">
		<div class="absolute left-3 flex items-center opacity-80">
			<router-link class="flex items-center" :to="{ name: 'home' }">
				<img src="/frappe_black.png" alt="logo" class="h-5 dark:hidden" />
				<img src="/frappe_white.png" alt="logo" class="hidden h-5 dark:block" />
				<h1 class="text-md font-semibold leading-5 text-gray-800 dark:text-gray-200">Builder</h1>
			</router-link>
		</div>
	</div>
	<section class="max-w-800 m-auto mb-32 flex w-3/4 flex-col pt-10">
		<div class="mb-6 flex items-center justify-between">
			<h1 class="text-sm font-bold uppercase text-gray-800 dark:text-zinc-400">My Pages</h1>
			<div class="flex gap-4">
				<Input
					class="h-7 rounded-md text-sm text-gray-800 hover:border-gray-400 focus:border-gray-400 focus:bg-gray-50 focus:ring-0 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:focus:border-zinc-200 focus:dark:border-zinc-700"
					type="text"
					placeholder="Filter by title or route"
					inputClass="w-full"
					v-model="filter"
					@input="
						(value: string) => {
							filter = value;
						}
					" />
				<Input
					type="select"
					class="h-7 rounded-md border-gray-400 text-sm text-gray-800 focus:border-gray-400 focus:bg-gray-50 focus:ring-0 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:focus:border-zinc-200 focus:dark:border-zinc-700"
					inputClass="w-32"
					v-model="typeFilter"
					:options="[
						{ label: 'All', value: '' },
						{ label: 'Draft', value: 'draft' },
						{ label: 'Published', value: 'published' },
						{ label: 'Unpublished', value: 'unpublished' },
					]" />
				<router-link :to="{ name: 'builder', params: { pageId: 'new' } }">
					<Button variant="solid" icon-left="plus">New</Button>
				</router-link>
			</div>
		</div>
		<div class="flex flex-wrap gap-6">
			<div v-if="!webPages.data || !webPages.data.length" class="flex flex-col items-center justify-center">
				<p class="mt-4 text-center text-gray-500">
					You don't have any pages yet. Click on the "+ New" button to create a new page.
				</p>
			</div>
			<div v-else-if="!pages.length" class="flex flex-col items-center justify-center">
				<p class="mt-4 text-center text-gray-500">No matching pages found.</p>
			</div>
			<router-link
				v-for="page in pages"
				:key="page.page_name"
				:to="{ name: 'builder', params: { pageId: page.page_name } }"
				class="max-w-[250px] flex-grow basis-52">
				<div
					class="group relative mr-2 w-full overflow-hidden rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
					<img
						width="250"
						height="140"
						:src="page.preview"
						onerror="this.src='/assets/builder/images/fallback.png'"
						class="w-full overflow-hidden rounded-lg bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
					<div class="flex items-center justify-between border-t-[1px] px-3 dark:border-zinc-800">
						<span class="inline-block max-w-[160px] py-2 text-sm text-gray-700 dark:text-zinc-200">
							<div class="flex items-center gap-1">
								<p class="truncate">
									{{ page.page_title || page.page_name }}
								</p>
								<!-- <div class="flex gap-1">
									<Tooltip text="Draft">
										<div class="h-2 w-2 rounded-full bg-gray-500" v-show="page.draft_blocks"></div>
									</Tooltip>
									<Tooltip text="Published">
										<div class="h-2 w-2 rounded-full bg-green-600" v-show="page.published"></div>
									</Tooltip>
								</div> -->
							</div>
							<UseTimeAgo v-slot="{ timeAgo }" :time="page.creation">
								<p class="mt-1 block text-xs text-gray-500">
									{{ timeAgo }}
								</p>
							</UseTimeAgo>
						</span>
						<Dropdown
							:options="[
								{ label: 'Duplicate', onClick: () => duplicatePage(page), icon: 'copy' },
								{ label: 'View in Desk', onClick: () => store.openInDesk(page), icon: 'arrow-up-right' },
								{ label: 'Delete', onClick: () => deletePage(page), icon: 'trash' },
							]"
							size="sm"
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
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { confirm } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Dropdown } from "frappe-ui";
import { computed, onActivated, ref } from "vue";

const store = useStore();
const filter = ref("");
const typeFilter = ref("");

const pages = computed(() =>
	(webPages.data || []).filter((page: BuilderPage) => {
		if (typeFilter.value) {
			if (
				(typeFilter.value === "published" && !page.published) ||
				(typeFilter.value === "unpublished" && page.published) ||
				(typeFilter.value === "draft" && !page.draft_blocks)
			) {
				return false;
			}
		}
		if (filter.value) {
			return (
				page.page_title?.toLowerCase().includes(filter.value.toLowerCase()) ||
				page.route?.toLowerCase().includes(filter.value.toLowerCase())
			);
		} else {
			return true;
		}
	})
);

const deletePage = async (page: BuilderPage) => {
	const confirmed = await confirm(`Are you sure you want to delete Page: ${page.page_name}?`);
	if (confirmed) {
		await webPages.delete.submit(page.name);
	}
};

const duplicatePage = async (page: BuilderPage) => {
	const pageCopy = { ...page };
	pageCopy.page_name = `${page.page_name}-copy`;
	pageCopy.page_title = `${page.page_title} Copy`;
	await webPages.insert.submit(pageCopy);
};

onActivated(() => {
	webPages.fetch();
});
</script>
