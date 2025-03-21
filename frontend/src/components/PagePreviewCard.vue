<template>
	<router-link
		:to="{ name: 'builder', params: { pageId: page.page_name } }"
		v-if="mode === 'grid'"
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
				<Dropdown :options="actions" size="sm" placement="right">
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
		v-if="mode === 'list'"
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
							<p class="mt-1 block text-xs text-gray-500">Edited {{ timeAgo }}</p>
						</UseTimeAgo>
					</div>
				</span>
				<div class="flex items-center gap-2">
					<Badge theme="green" v-if="page.published" class="dark:bg-green-900 dark:text-green-400">
						Published
					</Badge>
					<Dropdown :options="actions" size="sm" placement="right">
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
</template>
<script setup lang="ts">
import { webPages } from "@/data/webPage";
import useBuilderStore from "@/stores/builderStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { confirm, openInDesk } from "@/utils/helpers";
import { UseTimeAgo } from "@vueuse/components";
import { Badge, Dropdown, createDocumentResource } from "frappe-ui";

const builderStore = useBuilderStore();

const props = defineProps<{
	page: BuilderPage;
	mode: "grid" | "list";
}>();

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

const deletePage = async (page: BuilderPage) => {
	const confirmed = await confirm(
		`Are you sure you want to delete <b title=${page.page_name}>${page.page_title}</b>?`,
	);
	if (confirmed) {
		await webPages.delete.submit(page.name);
	}
};

const actions = [
	{
		label: "Duplicate",
		onClick: () => duplicatePage(props.page),
		icon: "copy",
	},
	{
		label: "View in Desk",
		onClick: () => openInDesk(props.page),
		icon: "arrow-up-right",
	},
	{
		label: "Delete",
		onClick: () => deletePage(props.page),
		icon: "trash",
	},
];
</script>
