<template>
	<div class="no-scrollbar flex-1 overflow-auto">
		<section class="m-auto mb-24 flex h-fit w-3/4 max-w-6xl flex-col pt-5">
			<!-- pages -->
			<div>
				<div v-if="!webPages.data?.length && !searchFilter && !typeFilter" class="col-span-full">
					<p class="px-3 text-base text-gray-500">
						You don't have any pages yet. Click on the "+ New" button to create a new page.
					</p>
				</div>
				<div v-else-if="!webPages.data?.length" class="col-span-full">
					<p class="px-3 text-base text-gray-500">No matching pages found.</p>
				</div>
				<!-- grid -->
				<div class="grid-col grid gap-3 auto-fill-[220px]" v-if="displayType === 'grid'">
					<PageCard
						v-for="page in webPages.data"
						:selected="selectedPages.has(page.name)"
						@click.capture="($event: MouseEvent) => handleClick($event, page)"
						:key="page.page_name"
						:page="page"
						v-on-click-and-hold="() => enableSelectionMode(page)"></PageCard>
				</div>
				<!-- list -->
				<div v-if="displayType === 'list'">
					<PageListItem
						@click.capture="($event: MouseEvent) => handleClick($event, page)"
						v-for="page in webPages.data"
						:selected="selectedPages.has(page.name)"
						:key="page.page_name"
						:page="page"
						v-on-click-and-hold="() => enableSelectionMode(page)"></PageListItem>
				</div>
				<!-- tree -->
				<div v-if="displayType === 'tree'">
					<RouteTreeView
						ref="routeTreeRef"
						class="pl-2 pr-3"
						:search-filter="searchFilter"
						:active-folder="builderStore.activeFolder" />
				</div>
			</div>
			<BuilderButton
				class="m-auto mt-12 w-fit text-sm"
				@click="loadMore"
				v-if="webPages.data?.length && webPages.hasNextPage && displayType !== 'tree'"
				variant="subtle"
				size="sm">
				Load More
			</BuilderButton>
		</section>
	</div>
	<SelectFolder
		v-model="showFolderSelectorDialog"
		:currentFolder="builderStore.activeFolder"
		@folderSelected="setFolder"></SelectFolder>
</template>

<script setup lang="ts">
import SelectFolder from "@/components/Modals/SelectFolder.vue";
import PageCard from "@/components/PageCard.vue";
import PageListItem from "@/components/PageListItem.vue";
import RouteTreeView from "@/components/RouteTreeView.vue";
import { useDashboardState } from "@/composables/useDashboardState";
import { webPages } from "@/data/webPage";
import vOnClickAndHold from "@/directives/vOnClickAndHold";
import useBuilderStore from "@/stores/builderStore";
import { BuilderPage } from "@/types/Builder/BuilderPage";
import { useShortcut } from "@/utils/useShortcut";
import { watchDebounced } from "@vueuse/core";
import { createResource } from "frappe-ui";
import { useTelemetry } from "frappe-ui/frappe";
import { onActivated, onMounted, onUnmounted, ref, watch } from "vue";

const routeTreeRef = ref<InstanceType<typeof RouteTreeView>>();

const { capture } = useTelemetry();
const builderStore = useBuilderStore();
const {
	searchFilter,
	typeFilter,
	orderBy,
	displayType,
	selectionMode,
	selectedPages,
	showFolderSelectorDialog,
	expandTreeFn,
	collapseTreeFn,
} = useDashboardState();

onMounted(() => {
	expandTreeFn.value = () => routeTreeRef.value?.expandAll();
	collapseTreeFn.value = () => routeTreeRef.value?.collapseAll();
});

onUnmounted(() => {
	expandTreeFn.value = null;
	collapseTreeFn.value = null;
});

const orderMap = {
	creation: "creation desc",
	modified: "modified desc",
	alphabetically_a_z: "page_title asc",
	alphabetically_z_a: "page_title desc",
};

onActivated(() => {
	capture("builder_dashboard_page_visited");
});

watch(
	() => builderStore.activeFolder,
	() => fetchPages(),
);

watch(displayType, () => fetchPages());

// remove selection mode when the escape key is pressed
useShortcut({
	key: "Escape",
	description: "Deselect pages",
	group: "Dashboard",
	handler: () => {
		selectedPages.value.clear();
		selectionMode.value = false;
	},
});

const fetchPages = () => {
	const filters = {
		is_template: 0,
	} as any;
	if (typeFilter.value && displayType.value !== "tree") {
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
	if (builderStore.activeFolder) {
		filters["project_folder"] = builderStore.activeFolder;
	}

	webPages.update({
		filters,
		orFilters,
		orderBy: orderMap[orderBy.value],
	});
	webPages.fetch();
};

const loadMore = () => {
	webPages.next();
};

const firstHold = ref(false);

const handleClick = (e: MouseEvent, page: BuilderPage) => {
	if (selectionMode.value) {
		e.preventDefault();
		e.stopPropagation();
		if (firstHold.value) {
			firstHold.value = false;
			return;
		}
		if (e.shiftKey) {
			const pages = webPages.data || [];
			// select all pages between the last selected page and the current page
			const lastSelectedPage = selectedPages.value.size
				? pages.find((p: BuilderPage) => p.name === Array.from(selectedPages.value)[0])
				: null;
			if (lastSelectedPage) {
				const lastSelectedPageIndex = pages.indexOf(lastSelectedPage);
				const currentPageIndex = pages.indexOf(page);
				const start = Math.min(lastSelectedPageIndex, currentPageIndex);
				const end = Math.max(lastSelectedPageIndex, currentPageIndex);
				for (let i = start; i <= end; i++) {
					const p = pages[i];
					selectedPages.value.add(p.name);
				}
			}
		} else if (e.ctrlKey || e.metaKey) {
			togglePageSelection(page);
		} else {
			selectedPages.value.clear();
			togglePageSelection(page);
		}
	} else {
		capture("builder_page_opened", { page_name: page.page_name });
	}
};

const enableSelectionMode = (page: BuilderPage) => {
	selectionMode.value = true;
	firstHold.value = true;
	togglePageSelection(page);
};

const togglePageSelection = (page: BuilderPage) => {
	if (selectedPages.value.has(page.name)) {
		selectedPages.value.delete(page.name);
	} else {
		selectedPages.value.add(page.name);
	}
	// Disable selection mode if no pages are selected
	if (!selectedPages.value.size) {
		selectionMode.value = false;
	}
};

watchDebounced([searchFilter, typeFilter, orderBy], fetchPages, {
	debounce: 300,
	immediate: true,
});

const setFolder = async (folder: string) => {
	createResource({
		method: "POST",
		url: "builder.api.update_page_folder",
	})
		.submit({
			pages: Array.from(selectedPages.value),
			folder_name: folder,
		})
		.then(() => {
			for (const pageName of selectedPages.value) {
				const page = webPages.data?.find((p: BuilderPage) => p.name === pageName);
				if (page) {
					page.project_folder = folder;
				}
			}
			selectedPages.value.clear();
			selectionMode.value = false;
			showFolderSelectorDialog.value = false;
			builderStore.activeFolder = folder;
		});
};
</script>
