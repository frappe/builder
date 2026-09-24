<template>
	<div class="border-b border-outline-gray-1 px-3 pb-2 pt-2" @click.stop>
		<div class="flex items-center justify-between">
			<button
				class="flex min-w-0 items-center gap-2 rounded-4 py-1 pr-1 text-sm text-ink-gray-7 hover:text-ink-gray-9"
				:aria-expanded="open"
				@click="open = !open">
				<span
					class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-5 transition-transform"
					:class="{ 'rotate-90': open }"
					aria-hidden="true" />
				<span class="flex min-w-0 items-center gap-1">
					<span class="font-medium">{{ __("Pages") }}</span>
					<span class="truncate text-ink-gray-5">· {{ folder }}</span>
				</span>
			</button>
			<Button
				size="sm"
				variant="ghost"
				icon="lucide-plus"
				:aria-label="newPageLabel"
				:tooltip="newPageLabel"
				@click="createPageIn(folder)" />
		</div>
		<template v-if="open">
			<BuilderInput
				v-if="pages.length > SEARCH_THRESHOLD"
				class="my-1"
				type="text"
				:placeholder="__('Search pages')"
				v-model="search"
				@input="(value: string) => (search = value)" />
			<div class="max-h-[30vh] overflow-y-auto">
				<PageRow v-for="page in visiblePages" :key="page.name" :page="page" :route-label="routeLabel(page)" />
				<p v-if="search && !visiblePages.length" class="px-2 py-1 text-sm text-ink-gray-5">
					{{ __("No pages match.") }}
				</p>
			</div>
		</template>
	</div>
</template>
<script setup lang="ts">
import PageRow from "@/components/LeftPanelTabs/PageRow.vue";
import usePageStore from "@/stores/pageStore";
import { __ } from "@/translation";
import { BuilderPage } from "@/types/doctypes";
import { createPageIn, folderPages, pagesVersion } from "@/utils/pageTree";
import { Button } from "frappe-ui";
import { useStorage } from "@vueuse/core";
import { computed, ref, watch } from "vue";

const SEARCH_THRESHOLD = 10;

const pageStore = usePageStore();
const open = useStorage("pagesSectionExpanded", false);
const search = ref("");

// the open page's folder is the "file" here: its pages are the ones listed
const folder = computed(() => pageStore.activePage?.project_folder || "");

// the open page's row mirrors unsaved title, route and folder edits
const pages = computed<BuilderPage[]>(() => {
	const active = pageStore.activePage;
	return (folderPages.data ?? [])
		.map((page: BuilderPage) => (active && page.name === active.name ? { ...page, ...active } : page))
		.filter((page: BuilderPage) => (page.project_folder || "") === folder.value);
});

// a shared first segment ("tide/") is implied by the folder, so rows show the rest
const routePrefix = computed(() => {
	if (!folder.value || !pages.value.length) return "";
	const first = pages.value[0].route?.split("/")[0];
	return pages.value.every((page) => page.route?.startsWith(`${first}/`)) ? `${first}/` : "";
});

const visiblePages = computed(() => {
	const query = search.value.trim().toLowerCase();
	if (!query) return pages.value;
	return pages.value.filter(
		(page) => page.page_title?.toLowerCase().includes(query) || page.route?.toLowerCase().includes(query),
	);
});

const routeLabel = (page: BuilderPage) => `/${(page.route || "").slice(routePrefix.value.length)}`;

const newPageLabel = computed(() => __("New page in {0}", [folder.value]));

function loadFolderPages() {
	folderPages.update({ filters: { is_template: 0, project_folder: folder.value } });
	folderPages.reload();
}

// the list only overlays the open page, so the page just left must come fresh from the server
watch(
	[() => pageStore.activePage?.name, folder],
	([name]) => {
		search.value = "";
		if (name && folder.value) loadFolderPages();
	},
	{ immediate: true },
);

watch(pagesVersion, loadFolderPages);
</script>
