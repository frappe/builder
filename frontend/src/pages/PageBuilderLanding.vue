<template>
	<div
		class="toolbar sticky top-0 z-10 flex h-14 items-center justify-center bg-white p-2 shadow-sm dark:border-b-[1px] dark:border-gray-800 dark:bg-zinc-900"
		ref="toolbar">
		<div class="absolute left-3 flex items-center">
			<router-link class="flex items-center gap-2" :to="{ name: 'home' }">
				<img src="/builder_logo.png" alt="logo" class="h-7" />
				<h1 class="text-md mt-[2px] font-semibold leading-5 text-gray-800 dark:text-gray-200">Builder</h1>
			</router-link>
		</div>
	</div>
	<section class="max-w-800 m-auto mb-32 flex w-3/4 flex-col pt-10">
		<div class="mb-6 flex items-center justify-between">
			<h1 class="text-sm font-bold uppercase text-gray-800 dark:text-zinc-400">My Pages</h1>
			<div class="flex gap-4">
				<TabButtons
					:buttons="[
						{ label: 'Grid', value: 'grid' },
						{ label: 'List', value: 'list' },
					]"
					v-model="displayType"
					class="w-fit self-end [&>div>button[aria-checked='false']]:dark:!bg-transparent [&>div>button[aria-checked='false']]:dark:!text-zinc-400 [&>div>button[aria-checked='true']]:dark:!bg-zinc-700 [&>div>button]:dark:!bg-zinc-700 [&>div>button]:dark:!text-zinc-100 [&>div]:dark:!bg-zinc-900"></TabButtons>
				<div class="relative flex">
					<Input
						class="h-7 rounded-md text-sm text-gray-800 hover:border-gray-400 focus:border-gray-400 focus:bg-gray-50 focus:ring-0 dark:border-zinc-800 dark:bg-zinc-900 dark:text-zinc-200 dark:focus:border-zinc-200 focus:dark:border-zinc-700"
						type="text"
						placeholder="Filter by title or route"
						inputClass="w-full"
						v-model="searchFilter"
						autofocus
						@input="
							(value: string) => {
								searchFilter = value;
							}
						" />
					<div
						class="absolute right-1 top-[3px] cursor-pointer p-1 text-gray-700 dark:text-zinc-300"
						@click="searchFilter = ''"
						v-show="searchFilter">
						<CrossIcon />
					</div>
				</div>
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
			<div
				v-if="!webPages.data?.length && !searchFilter && !typeFilter"
				class="flex flex-col items-center justify-center">
				<p class="mt-4 text-center text-base text-gray-500">
					You don't have any pages yet. Click on the "+ New" button to create a new page.
				</p>
			</div>
			<div v-else-if="!webPages.data?.length" class="flex flex-col items-center justify-center">
				<p class="mt-4 text-center text-base text-gray-500">No matching pages found.</p>
			</div>
			<router-link
				v-if="displayType === 'grid'"
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
						onerror="this.src='/assets/builder/images/fallback.png'"
						class="w-full overflow-hidden rounded-lg bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
					<div class="flex items-center justify-between border-t-[1px] px-3 dark:border-zinc-800">
						<span class="inline-block max-w-[160px] py-2 text-sm text-gray-700 dark:text-zinc-200">
							<div class="flex items-center gap-1">
								<p class="truncate">
									{{ page.page_title || page.page_name }}
								</p>
							</div>
							<UseTimeAgo v-slot="{ timeAgo }" :time="page.modified">
								<p class="mt-1 block text-xs text-gray-500">Edited {{ timeAgo }}</p>
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
									class="h-4 w-4 text-gray-500 hover:text-gray-700"
									@click="open"></FeatherIcon>
							</template>
						</Dropdown>
					</div>
				</div>
			</router-link>
			<router-link
				v-for="page in webPages.data"
				v-if="displayType === 'list'"
				:key="page.page_name"
				:to="{ name: 'builder', params: { pageId: page.page_name } }"
				class="h-fit w-full flex-grow">
				<div
					class="group relative mr-2 flex w-full overflow-hidden rounded-md shadow hover:cursor-pointer dark:border-zinc-700 dark:bg-zinc-900 dark:text-zinc-200">
					<img
						width="250"
						height="140"
						:src="page.preview"
						onerror="this.src='/assets/builder/images/fallback.png'"
						class="block w-44 overflow-hidden rounded-lg bg-gray-50 object-cover p-2 dark:bg-zinc-900" />
					<div class="flex flex-1 items-start justify-between border-t-[1px] p-3 px-3 dark:border-zinc-800">
						<span class="flex h-full flex-col justify-between text-sm text-gray-700 dark:text-zinc-200">
							<div>
								<div class="flex items-center gap-1">
									<p class="truncate">
										{{ page.page_title || page.page_name }}
									</p>
								</div>
								<div class="mt-2 flex items-center gap-1">
									<FeatherIcon name="globe" class="h-3 w-3 text-gray-500 hover:text-gray-700"></FeatherIcon>
									<p class="text-xs text-gray-600">
										{{ page.route }}
									</p>
								</div>
							</div>
							<div class="flex items-baseline gap-1">
								<p class="mt-1 block text-xs text-gray-500">Created By {{ page.owner }}</p>
								·
								<UseTimeAgo v-slot="{ timeAgo }" :time="page.modified">
									<p class="mt-1 block text-xs text-gray-500">
										Edited {{ timeAgo }} by {{ page.modified_by }}
									</p>
								</UseTimeAgo>
							</div>
						</span>
						<div class="flex items-center gap-2">
							<Badge theme="green" v-if="page.published" class="dark:bg-green-900 dark:text-green-400">
								Published
							</Badge>
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
										class="h-4 w-4 text-gray-500 hover:text-gray-700"
										@click="open"></FeatherIcon>
								</template>
							</Dropdown>
						</div>
					</div>
				</div>
			</router-link>
		</div>
		<Button
			class="m-auto mt-12 w-fit text-sm dark:bg-zinc-900 dark:text-zinc-300"
			@click="loadMore"
			v-show="webPages.hasNextPage"
			variant="subtle"
			size="sm">
			Load More
		</Button>
	</section>
</template>
<script setup lang="ts">
import CrossIcon from "@/components/Icons/Cross.vue";
import { webPages } from "@/data/webPage";
import useStore from "@/store";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { confirm } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { useStorage, watchDebounced } from "@vueuse/core";
import { Badge, Dropdown, TabButtons, createDocumentResource } from "frappe-ui";
import { ref } from "vue";

const displayType = useStorage("displayType", "grid");

const store = useStore();
const searchFilter = ref("");
const typeFilter = ref("");

watchDebounced(
	[searchFilter, typeFilter],
	() => {
		const filters = {} as any;
		if (typeFilter.value) {
			if (typeFilter.value === "published") {
				filters["published"] = true;
			} else if (typeFilter.value === "unpublished") {
				filters["published"] = false;
			} else if (typeFilter.value === "draft") {
				filters["draft_blocks"] = ["is", "set"];
			}
		}
		const orFilters = {} as any;
		if (searchFilter.value) {
			orFilters["page_title"] = ["like", `%${searchFilter.value}%`];
			orFilters["route"] = ["like", `%${searchFilter.value}%`];
		}
		webPages.update({
			filters,
			orFilters,
		});
		webPages.fetch();
	},
	{ debounce: 300 },
);

const deletePage = async (page: BuilderPage) => {
	const confirmed = await confirm(`Are you sure you want to delete Page: ${page.page_name}?`);
	if (confirmed) {
		await webPages.delete.submit(page.name);
	}
};

const duplicatePage = async (page: BuilderPage) => {
	const webPageResource = await createDocumentResource({
		doctype: "Builder Page",
		name: page.page_name,
		auto: true,
	});
	await webPageResource.get.promise;

	const pageCopy = webPageResource.doc as BuilderPage;
	pageCopy.page_name = `${pageCopy.page_name}-copy`;
	pageCopy.page_title = `${pageCopy.page_title} Copy`;
	await webPages.insert.submit(pageCopy);
};

const loadMore = () => {
	webPages.next();
};
</script>
