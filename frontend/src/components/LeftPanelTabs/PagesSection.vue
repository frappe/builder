<template>
	<div class="border-b border-outline-gray-1 px-3 pb-2 pt-2" @click.stop>
		<div class="flex items-center justify-between">
			<button
				class="flex min-w-0 items-center gap-2 rounded-4 py-1 pr-1 text-sm text-ink-gray-7 hover:text-ink-gray-9"
				:aria-expanded="open"
				:aria-label="__('Pages in {0}', [folder])"
				@click="open = !open">
				<span
					class="lucide-chevron-right size-3.5 shrink-0 text-ink-gray-5 transition-transform"
					:class="{ 'rotate-90': open }"
					aria-hidden="true" />
				<span class="flex min-w-0 items-center gap-1.5">
					<span class="lucide-folder size-3.5 shrink-0 text-ink-gray-5" aria-hidden="true" />
					<span class="truncate font-medium">{{ folder }}</span>
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
				v-if="showSearch"
				class="my-1"
				type="text"
				:placeholder="__('Search pages')"
				v-model="search"
				@input="(value: string) => (search = value)" />
			<div class="no-scrollbar -mx-1 max-h-[30vh] space-y-0.5 overflow-y-auto">
				<PageRow v-for="page in pages" :key="page.name" :page="page" :route-label="routeLabel(page)" />
				<p v-if="search && !pages.length" class="px-2 py-1 text-sm text-ink-gray-5">
					{{ __("No pages match.") }}
				</p>
				<p v-else-if="!search && isCapped" class="px-2 py-1 text-p-sm text-ink-gray-5">
					{{ __("Showing the first {0} pages. Search to find the rest.", [FOLDER_PAGE_LIMIT]) }}
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
import { createPageIn, FOLDER_PAGE_LIMIT, folderPages, pagesVersion } from "@/utils/pageActions";
import { Button } from "frappe-ui";
import { useDebounceFn, useEventListener, useStorage } from "@vueuse/core";
import { computed, ref, watch } from "vue";

const SEARCH_THRESHOLD = 10;

const pageStore = usePageStore();
const open = useStorage("pagesSectionExpanded", false);
const search = ref("");

// capture phase, since a selected block stops the press to start a reorder drag
useEventListener(
	document,
	"pointerdown",
	(event) => {
		if ((event.target as Element).closest?.("[data-builder-canvas] [data-block-id]")) open.value = false;
	},
	{ capture: true },
);

// the open page's folder is the "file" here: its pages are the ones listed
const folder = computed(() => pageStore.activePage?.project_folder || "");

const matchesSearch = (page: BuilderPage) => {
	const query = search.value.trim().toLowerCase();
	return (
		!query ||
		Boolean(page.page_title?.toLowerCase().includes(query) || page.route?.toLowerCase().includes(query))
	);
};

// the open page's row mirrors its unsaved title, route and folder, and is matched against the
// search here, since the server may not have its latest title or route yet
const pages = computed<BuilderPage[]>(() => {
	const active = pageStore.activePage;
	const rows = (folderPages.data ?? [])
		.map((page: BuilderPage) => (active && page.name === active.name ? { ...page, ...active } : page))
		.filter((page: BuilderPage) => (page.project_folder || "") === folder.value);
	// templates stay out of the list like on the server, even when one is the open page
	if (!active || active.is_template || (active.project_folder || "") !== folder.value) return rows;
	const others = rows.filter((page) => page.name !== active.name);
	if (!matchesSearch(active)) return others;
	return others.length === rows.length ? [active, ...others] : rows;
});

// a shared first segment ("tide/") is implied by the folder, so rows show the rest
const routePrefix = computed(() => {
	if (!folder.value || !pages.value.length) return "";
	const first = pages.value[0].route?.split("/")[0];
	return pages.value.every((page) => page.route?.startsWith(`${first}/`)) ? `${first}/` : "";
});

// search runs on the server, so it also reaches pages past the loaded limit
const showSearch = computed(() => Boolean(search.value) || pages.value.length > SEARCH_THRESHOLD);
const isCapped = computed(() => (folderPages.data?.length ?? 0) >= FOLDER_PAGE_LIMIT);

const routeLabel = (page: BuilderPage) => `/${(page.route || "").slice(routePrefix.value.length)}`;

const newPageLabel = computed(() => __("New page in {0}", [folder.value]));

let loadedQuery = "";

function loadFolderPages() {
	// while collapsed, clear the list instead of loading it, so nothing reads a stale copy
	if (!open.value) return void (folderPages.data = null);
	const query = search.value.trim();
	loadedQuery = query;
	folderPages.update({
		filters: { is_template: 0, project_folder: folder.value },
		orFilters: query ? { page_title: ["like", `%${query}%`], route: ["like", `%${query}%`] } : {},
	});
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

watch([open, pagesVersion], loadFolderPages);
// a page switch clears the search and loads right away, so skip a query that is already loaded
watch(
	search,
	useDebounceFn(() => search.value.trim() !== loadedQuery && loadFolderPages(), 300),
);
</script>
